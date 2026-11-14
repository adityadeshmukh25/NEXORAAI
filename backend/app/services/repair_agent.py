import json
import re
from pathlib import PurePosixPath

from app.services.ollama_service import ollama_service


class RepairAgent:

    MAX_JSON_RETRIES = 2

    ROOT_CONFIG_FILES = {
        "requirements.txt", "pyproject.toml", "setup.py",
        "setup.cfg", "package.json", "tsconfig.json", ".gitignore",
    }

    ALLOWED_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".css",
        ".json", ".html", ".md", ".txt", ".toml",
        ".yaml", ".yml", ".sql",
    }

    def __init__(self, ollama_service):
        self.ollama_service = ollama_service

    @staticmethod
    def normalize_path(path):
        path = str(path).replace("\\", "/").strip()
        while path.startswith("./"):
            path = path[2:]
        return path

    def classify_errors(self, errors):
        groups = {"backend": [], "frontend": [], "general": []}
        for error in errors:
            message = str(error)
            normalized = message.replace("\\", "/")
            if "backend/" in normalized:
                groups["backend"].append(message)
            elif "frontend/" in normalized:
                groups["frontend"].append(message)
            else:
                groups["general"].append(message)
        return groups

    def select_files(self, project_files, area, errors=None):
        normalized_files = {
            self.normalize_path(path): content
            for path, content in project_files.items()
        }

        if area == "general":
            return {
                path: content
                for path, content in normalized_files.items()
                if path in self.ROOT_CONFIG_FILES
            }

        prefix = "backend/" if area == "backend" else "frontend/"
        area_files = {
            path: content
            for path, content in normalized_files.items()
            if path.startswith(prefix)
        }

        # When validation identifies exact paths, give the model only those
        # files plus the relevant frontend package manifest.
        referenced = []
        for error in errors or []:
            match = re.search(
                r"((?:backend|frontend)/[A-Za-z0-9_./-]+\."
                r"(?:py|ts|tsx|js|jsx|css|json|html|md|txt|toml|yaml|yml|sql))",
                str(error).replace("\\", "/"),
            )
            if match:
                path = self.normalize_path(match.group(1))
                if path in area_files and path not in referenced:
                    referenced.append(path)

        if referenced:
            selected = {path: area_files[path] for path in referenced}
            if area == "frontend" and "frontend/package.json" in area_files:
                selected["frontend/package.json"] = area_files[
                    "frontend/package.json"
                ]
            return selected

        return area_files

    def parse_response(self, response):
        if isinstance(response, dict):
            return response
        if not isinstance(response, str):
            raise ValueError(
                f"Unexpected model response type: {type(response).__name__}"
            )

        content = response.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            result = json.loads(content.lstrip("\ufeff"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON from repair model: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise ValueError("Repair response must be a JSON object.")
        return result

    def validate_response(self, result):
        if not isinstance(result, dict):
            raise ValueError("Repair response must be an object.")

        files = result.get("files")
        if not isinstance(files, list):
            raise ValueError("Repair response must contain a files array.")

        seen = set()
        validated = []

        for item in files:
            if not isinstance(item, dict):
                raise ValueError("Each file operation must be an object.")

            raw_path = item.get("path")
            action = item.get("action")
            content = item.get("content")

            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("Every operation needs a valid file path.")

            path = self.normalize_path(raw_path)
            pure_path = PurePosixPath(path)

            if (
                not path or pure_path.is_absolute()
                or ".." in pure_path.parts or ":" in path
                or path.startswith("/")
            ):
                raise ValueError(f"Unsafe file path: {path}")

            if pure_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                raise ValueError(f"Unsupported file extension: {path}")
            if path in seen:
                raise ValueError(f"Duplicate file operation: {path}")
            seen.add(path)

            if action not in {"create", "update", "delete"}:
                raise ValueError(f"Unsupported action: {action}")

            # The repair workflow intentionally does not delete project files.
            if action == "delete":
                continue

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"{action} requires complete file content: {path}"
                )

            validated.append({
                "path": path,
                "action": action,
                "content": content,
            })

        result["files"] = validated
        result.setdefault("summary", "Autonomous repair generated.")
        result.setdefault("root_causes", [])
        return result

    def validate_batch_scope(self, result, area, supplied_files):
        valid_files = []

        for item in result["files"]:
            path = item["path"]
            action = item["action"]

            if area == "backend":
                allowed = path.startswith("backend/")
            elif area == "frontend":
                allowed = path.startswith("frontend/")
            else:
                allowed = path in self.ROOT_CONFIG_FILES

            if not allowed:
                continue

            if action == "create" and path in supplied_files:
                item["action"] = "update"
                action = "update"

            if action == "update" and path not in supplied_files:
                continue

            valid_files.append(item)

        result["files"] = valid_files
        return result

    @staticmethod
    def set_file_operation(result, selected_files, path, content):
        action = "update" if path in selected_files else "create"
        operation = {"path": path, "action": action, "content": content}

        existing = next(
            (item for item in result["files"] if item["path"] == path),
            None,
        )
        if existing:
            existing.update(operation)
        else:
            result["files"].append(operation)

    def repair_react_router_routes(self, errors, project_files):
        """Deterministically fix common React Router v5 route validation errors."""
        route_errors = [
            str(error) for error in errors
            if any(token in str(error).lower() for token in (
                "homepage route", "fallback route", "exact attribute"
            ))
        ]
        if not route_errors:
            return None

        normalized_files = {
            self.normalize_path(path): content
            for path, content in project_files.items()
        }

        app_path = None
        for error in route_errors:
            match = re.search(
                r"(frontend/[A-Za-z0-9_./-]*App\.(?:tsx|ts|jsx|js))",
                error.replace("\\", "/"),
                re.IGNORECASE,
            )
            if match:
                candidate = self.normalize_path(match.group(1))
                if candidate in normalized_files:
                    app_path = candidate
                    break

        if app_path is None:
            for candidate in (
                "frontend/src/App.tsx",
                "frontend/src/App.ts",
                "frontend/src/App.jsx",
                "frontend/src/App.js",
            ):
                if candidate in normalized_files:
                    app_path = candidate
                    break

        if app_path is None:
            raise ValueError(
                "React Router errors were found, but no frontend App file "
                "was supplied to the repair agent."
            )

        source = normalized_files[app_path]
        if not isinstance(source, str):
            raise ValueError(f"{app_path} does not contain text.")

        switch_open = re.search(r"<Switch\b[^>]*>", source)
        switch_close = re.search(r"</Switch\s*>", source)
        if not switch_open or not switch_close:
            raise ValueError(
                f"{app_path} does not contain a React Router v5 Switch. "
                "Automatic route repair could not safely continue."
            )

        route_pattern = re.compile(
            r"<Route\b[^>]*\bpath\s*=\s*(['\"])(.*?)\1[^>]*?/?>",
            re.DOTALL,
        )
        route_matches = list(route_pattern.finditer(source))
        route_paths = [
            match.group(2).strip()
            for match in route_matches
            if match.group(2).strip()
        ]

        # Add exact to parent routes when a later route is nested beneath it.
        replacements = []
        for match in route_matches:
            route_path = match.group(2).strip()
            has_nested = any(
                other.startswith(route_path.rstrip("/") + "/")
                for other in route_paths
                if other != route_path
            )
            tag = match.group(0)
            if has_nested and not re.search(r"\bexact\b", tag):
                insertion = tag.find("<Route") + len("<Route")
                tag = tag[:insertion] + " exact" + tag[insertion:]
                replacements.append((match.start(), match.end(), tag))

        for start, end, replacement in reversed(replacements):
            source = source[:start] + replacement + source[end:]

        # Choose the first existing non-root route as the homepage destination.
        route_paths = [
            match.group(2).strip()
            for match in route_pattern.finditer(source)
            if match.group(2).strip() not in {"", "/"}
        ]
        redirect_target = next(
            (path for path in route_paths if path.startswith("/")),
            route_paths[0] if route_paths else None,
        )

        switch_open = re.search(r"<Switch\b[^>]*>", source)
        switch_close = re.search(r"</Switch\s*>", source)
        if not switch_open or not switch_close:
            raise ValueError("Could not locate the React Router Switch block.")

        root_route_exists = bool(re.search(
            r"<(?:Route|Redirect)\b[^>]*\b(?:path|from)\s*=\s*(['\"])/\1",
            source,
        ))

        additions = []
        needs_redirect_import = False

        if not root_route_exists:
            if not redirect_target:
                raise ValueError(
                    "Cannot add a homepage redirect because no existing "
                                       "application route was found."
                )
            additions.append(
                f'\n        <Redirect exact from="/" to="{redirect_target}" />'
            )
            needs_redirect_import = True

        fallback_exists = bool(re.search(
            r"<Route\b[^>]*(?:\bpath\s*=\s*(['\"])\*\1|"
            r"\bpath\s*=\s*{[^}]*\*[^}]*})",
            source,
        ))
        # A Route without a path is also a valid final fallback.
        no_path_route_exists = any(
            not re.search(r"\bpath\s*=", match.group(0))
            for match in re.finditer(r"<Route\b[^>]*?/?>", source)
        )

        if not fallback_exists and not no_path_route_exists:
            additions.append(
                "\n        <Route render={() => <div>Page not found</div>} />"
            )

        if additions:
            source = (
                source[:switch_close.start()]
                + "".join(additions)
                + "\n      "
                + source[switch_close.start():]
            )

        if needs_redirect_import:
            import_pattern = re.compile(
                r"(import\s*\{)([^}]*)(\}\s*from\s*['\"]react-router-dom['\"]\s*;)"
            )
            import_match = import_pattern.search(source)

            if import_match:
                imported_names = import_match.group(2)
                if not re.search(r"\bRedirect\b", imported_names):
                    updated_names = imported_names.rstrip() + ", Redirect "
                    source = (
                        source[:import_match.start(2)]
                        + updated_names
                        + source[import_match.end(2):]
                    )
            elif "from 'react-router-dom'" in source or \
                    'from "react-router-dom"' in source:
                raise ValueError(
                    "Could not safely add Redirect to the existing "
                    "react-router-dom import."
                )
            else:
                source = (
                    "import { Redirect } from 'react-router-dom';\n"
                    + source
                )

        return {
            "summary": (
                "Automatically repaired React Router homepage, "
                "nested route matching, and fallback handling."
            ),
            "root_causes": [
                "The React Router v5 Switch did not define a homepage "
                "or fallback route, and parent routes could shadow nested routes."
            ],
            "files": [{
                "path": app_path,
                "action": "update",
                "content": source,
            }],
        }

    def ensure_frontend_dependencies(self, result, selected_files, errors):
        error_text = " ".join(str(error).lower() for error in errors)
        needs_router = "react-router-dom" in error_text
        needs_typescript = "typescript" in error_text

        if not needs_router and not needs_typescript:
            return result

        package_path = "frontend/package.json"
        original_content = selected_files.get(package_path)
        if not original_content:
            raise ValueError(
                "Cannot repair frontend dependencies: "
                "original package.json was not supplied."
            )

        try:
            package = json.loads(original_content.lstrip("\ufeff"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Existing frontend/package.json is invalid."
            ) from exc

        if not isinstance(package, dict):
            raise ValueError(
                "Existing frontend/package.json must contain an object."
            )

        dependencies = package.setdefault("dependencies", {})
        dev_dependencies = package.setdefault("devDependencies", {})

        if not isinstance(dependencies, dict):
            raise ValueError("package.json dependencies must be an object.")
        if not isinstance(dev_dependencies, dict):
            raise ValueError(
                "package.json devDependencies must be an object."
            )

        if needs_router:
            dependencies["react-router-dom"] = "^5.3.4"
            dev_dependencies.setdefault(
                "@types/react-router-dom", "^5.3.3"
            )
        if needs_typescript:
            dev_dependencies["typescript"] = "^4.9.5"

        self.set_file_operation(
            result,
            selected_files,
            package_path,
            json.dumps(package, indent=2) + "\n",
        )
        return result

    def ensure_frontend_entry(self, result, selected_files, errors):
        error_text = " ".join(str(error).lower() for error in errors)
        package_content = selected_files.get("frontend/package.json", "")

        try:
            package = (
                json.loads(package_content.lstrip("\ufeff"))
                if package_content else {}
            )
        except json.JSONDecodeError:
            package = {}

        dependencies = package.get("dependencies", {})
        dev_dependencies = package.get("devDependencies", {})
        scripts = package.get("scripts", {})

        if not isinstance(dependencies, dict):
            dependencies = {}
        if not isinstance(dev_dependencies, dict):
            dev_dependencies = {}
        if not isinstance(scripts, dict):
            scripts = {}

        all_dependencies = set(dependencies) | set(dev_dependencies)
        uses_cra = (
            "react-scripts" in all_dependencies
            or any(
                isinstance(value, str) and "react-scripts" in value
                for value in scripts.values()
            )
        )
        if not uses_cra:
            return result

        needs_index = any(token in error_text for token in (
            "src/index.tsx", "src/index.js", "entrypoint is missing",
            "create react app entrypoint",
        ))
        needs_html = (
            "public/index.html" in error_text
            or "required frontend file is missing" in error_text
        )

        if needs_index:
            index_content = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element with id "root" was not found.');
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
            self.set_file_operation(
                result, selected_files,
                "frontend/src/index.tsx", index_content,
            )

        if needs_html:
            html_content = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#ffffff" />
    <title>Generated Application</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this application.</noscript>
    <div id="root"></div>
  </body>
</html>
"""
            self.set_file_operation(
                result, selected_files,
                "frontend/public/index.html", html_content,
            )

        return result

    def build_prompt(
        self, area, errors, project_files,
        context=None, previous_error=None,
    ):
        if area == "backend":
            instructions = """
BACKEND RULES:
- Python package root is backend/app.
- Use imports such as from app.models import Product.
- Never use backend.app.models or backend.app.database.
- Inspect actual supplied source code before choosing class names.
- Do not invent modules, functions, or imports.
- Do not modify frontend files.
"""
        elif area == "frontend":
            instructions = """
FRONTEND RULES:
- This project uses React and TypeScript.
- Existing router code uses Switch and component props.
- Use react-router-dom version 5, not version 6.
- Inspect exact component filenames before writing imports.
- Do not modify backend files.
- Use update for supplied files and create only for missing files.
- Return complete source code.
"""
        else:
            instructions = """
GENERAL CONFIGURATION RULES:
- Inspect existing configuration before modifying it.
- Preserve dependencies and scripts.
- Do not modify application source files.
"""

        context_text = (
            json.dumps(
                context, indent=2, ensure_ascii=False, default=str
            )
            if isinstance(context, (dict, list))
            else str(context or "No additional context.")
        )
        previous_text = (
            f"\nPREVIOUS ERROR:\n{previous_error}\n"
            if previous_error else ""
        )

        return f"""
You are a senior autonomous software engineer.
Repair the existing project using only the actual supplied files.

REPAIR AREA:
{area}

VALIDATION ERRORS:
{json.dumps(errors, indent=2)}

ACTUAL PROJECT FILES:
{json.dumps(project_files, indent=2, ensure_ascii=False)}

PROJECT CONTEXT:
{context_text}

{instructions}
{previous_text}

STRICT RULES:
1. Fix every listed validation error.
2. Inspect supplied source code before generating changes.
3. Never guess class names, module names, or file names.
4. Create files only when they do not already exist.
5. Never delete files.
6. Return complete file contents, not partial snippets.
7. Preserve existing functionality.
8. Ensure imports match actual filenames.
9. Do not return placeholder implementations.
10. Keep changes within the specified repair area.
11. Do not modify frontend/package.json; dependency changes are deterministic.
12. Do not omit files that have reported errors.
13. Do not modify files that are not required to fix the listed errors.

Return ONLY valid JSON:
{{
  "summary": "Brief repair summary",
  "root_causes": ["Root cause"],
  "files": [
    {{
      "path": "frontend/src/App.tsx",
      "action": "update",
      "content": "Complete corrected file content"
    }}
  ]
}}
Allowed actions: create and update.
No Markdown fences. No explanations outside JSON.
"""

    async def repair_batch(self, area, errors, project_files, context=None):
        selected_files = self.select_files(
            project_files, area, errors=errors
        )
        if not selected_files:
            raise ValueError(
                f"No project files available for {area} repair."
            )

        last_error = None
        for retry in range(self.MAX_JSON_RETRIES + 1):
            prompt = self.build_prompt(
                area=area,
                errors=errors,
                project_files=selected_files,
                context=context,
                previous_error=last_error,
            )
            try:
                response = await self.ollama_service.generate_json(prompt)
                result = self.parse_response(response)

                if isinstance(result.get("files"), list):
                    result["files"] = [
                        item for item in result["files"]
                        if not (
                            isinstance(item, dict)
                            and self.normalize_path(
                                item.get("path", "")
                            ) == "frontend/package.json"
                        )
                    ]

                result = self.validate_response(result)
                result = self.validate_batch_scope(
                    result, area, selected_files
                )

                if area == "frontend":
                    result = self.ensure_frontend_dependencies(
                        result, selected_files, errors
                    )
                    result = self.ensure_frontend_entry(
                        result, selected_files, errors
                    )

                if not result["files"]:
                    raise ValueError(
                        "Model did not propose any valid file changes "
                        "and no deterministic repair was required."
                    )

                result["area"] = area
                return result

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if retry >= self.MAX_JSON_RETRIES:
                    raise ValueError(
                        f"{area} repair failed after {retry + 1} attempts: "
                        f"{last_error}"
                    ) from exc

        raise ValueError(f"{area} repair failed.")

    async def repair(
        self, errors, project_files, attempt=None, context=None, **kwargs
    ):
        if not errors:
            return {
                "summary": "No repair required.",
                "root_causes": [],
                "files": [],
                "batches": [],
            }

        # Apply deterministic route repairs before involving the LLM.
        # This prevents the model from editing unrelated files such as example.tsx.
        route_result = self.repair_react_router_routes(
            errors, project_files
        )

        working_files = dict(project_files)
        combined_files = {}
        batch_results = []
        root_causes = []
        summaries = []

        remaining_errors = list(errors)

        if route_result:
            for item in route_result["files"]:
                combined_files[item["path"]] = item
                working_files[item["path"]] = item["content"]

            route_error_tokens = (
                "react router",
                "homepage route",
                "fallback route",
                "exact attribute",
            )
            remaining_errors = [
                error for error in remaining_errors
                if not any(
                    token in str(error).lower()
                    for token in route_error_tokens[1:]
                )
            ]

            batch_results.append({
                "area": "frontend",
                "summary": route_result["summary"],
                "files_changed": len(route_result["files"]),
                "method": "deterministic",
            })
            summaries.append(route_result["summary"])
            root_causes.extend(route_result["root_causes"])

        if not remaining_errors:
            return {
                "summary": " ".join(summaries),
                "root_causes": root_causes,
                "files": list(combined_files.values()),
                "batches": batch_results,
            }

        groups = self.classify_errors(remaining_errors)

        for area in ("backend", "frontend", "general"):
            area_errors = groups[area]
            if not area_errors:
                continue

            if not self.select_files(
                working_files, area, errors=area_errors
            ):
                raise ValueError(
                    f"No matching project files supplied for {area}: "
                    f"{area_errors}"
                )

            result = await self.repair_batch(
                area=area,
                errors=area_errors,
                project_files=working_files,
                context=context,
            )

            for item in result["files"]:
                path = item["path"]
                if path in combined_files:
                    # Merge deterministic and model edits to the same path
                    # only if the model was given the updated working copy.
                    combined_files[path] = item
                else:
                    combined_files[path] = item
                working_files[path] = item["content"]

            batch_results.append({
                "area": area,
                "summary": result.get("summary", ""),
                "files_changed": len(result["files"]),
            })
            summaries.append(result.get("summary", ""))
            root_causes.extend(result.get("root_causes", []))

        return {
            "summary": " ".join(
                summary for summary in summaries if summary
            ) or "Autonomous repair completed.",
            "root_causes": root_causes,
            "files": list(combined_files.values()),
            "batches": batch_results,
        }


repair_agent = RepairAgent(ollama_service)
