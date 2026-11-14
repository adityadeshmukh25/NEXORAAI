import ast
import json
import posixpath
import re

from pathlib import Path, PurePosixPath


class ProjectStructureValidator:

    SOURCE_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx",
        ".css", ".html", ".json", ".md",
        ".txt", ".toml", ".yaml", ".yml", ".sql",
    }

    FRONTEND_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}

    EXCLUDED_DIRECTORIES = {
        "node_modules", ".git", "__pycache__", ".venv", "venv"
    }

    IMPORT_PATTERN = re.compile(
        r"""(?:import|export)\s+(?:[\s\S]*?\s+from\s+)?["']([^"']+)["']"""
        r"""|import\s*["']([^"']+)["']"""
    )

    NODE_BUILTINS = {
        "assert", "buffer", "crypto", "events", "fs", "http",
        "https", "os", "path", "process", "stream", "url",
        "util", "zlib",
    }

    def validate_generation(self, generation):

        workspace = (
            Path(__file__).resolve().parents[2]
            / "generated_projects"
            / f"project_{generation.project_id}"
            / f"generation_{generation.id}"
        ).resolve()

        file_map = {}
        errors = []
        warnings = []
        results = []

        # Load database records, preferring actual disk contents.
        for item in generation.generated_files or []:

            if not isinstance(item, dict):
                continue

            raw_path = item.get("path", "")

            if not isinstance(raw_path, str) or not raw_path:
                continue

            normalized = raw_path.replace("\\", "/")
            relative = PurePosixPath(normalized)

            if (
                relative.is_absolute()
                or ".." in relative.parts
                or ":" in normalized
            ):
                errors.append(f"Unsafe generated file path: {raw_path}")
                continue

            destination = workspace.joinpath(*relative.parts).resolve()

            if not destination.is_relative_to(workspace):
                errors.append(f"File outside generation workspace: {raw_path}")
                continue

            if destination.is_file():
                content = destination.read_text(
                    encoding="utf-8-sig",
                    errors="replace"
                )
            else:
                content = item.get("content", "")

            if isinstance(content, str):
                file_map[relative.as_posix()] = content

        # Include supported files that exist on disk.
        if workspace.exists():

            for destination in workspace.rglob("*"):

                if not destination.is_file():
                    continue

                relative = destination.relative_to(workspace)

                if any(
                    part in self.EXCLUDED_DIRECTORIES
                    for part in relative.parts
                ):
                    continue

                if destination.suffix.lower() not in self.SOURCE_EXTENSIONS:
                    continue

                resolved = destination.resolve()

                if not resolved.is_relative_to(workspace):
                    continue

                file_map[relative.as_posix()] = destination.read_text(
                    encoding="utf-8-sig",
                    errors="replace"
                )

        normalized_paths = {path.lower() for path in file_map}

        # Validate Python syntax and local imports.
        python_modules = set()
        python_packages = set()

        for file_path in file_map:

            path = PurePosixPath(file_path)

            if path.suffix.lower() != ".py":
                continue

            parts = list(path.with_suffix("").parts)

            if parts and parts[0] == "backend":
                parts = parts[1:]

            if parts and parts[-1] == "__init__":
                parts.pop()

            if parts:
                python_modules.add(".".join(parts))

                for index in range(1, len(parts) + 1):
                    python_packages.add(".".join(parts[:index]))

        def module_exists(name):
            return (
                not name
                or name in python_modules
                or name in python_packages
            )

        for file_path, content in file_map.items():

            if not file_path.endswith(".py"):
                continue

            file_errors = []

            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as error:
                message = (
                    f"Python syntax error at line {error.lineno}, "
                    f"column {error.offset}: {error.msg}"
                )
                errors.append(f"{file_path}: {message}")
                results.append({
                    "file": file_path,
                    "status": "invalid",
                    "issues": [message],
                })
                continue

            source_path = PurePosixPath(file_path)
            package_parts = list(source_path.parent.parts)

            if package_parts and package_parts[0] == "backend":
                package_parts = package_parts[1:]

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):

                    for alias in node.names:
                        root = alias.name.split(".")[0]

                        if root in {"app", "backend"}:
                            if not module_exists(alias.name):
                                file_errors.append(
                                    f"Local module not found: {alias.name}"
                                )

                elif isinstance(node, ast.ImportFrom):

                    if node.level > 0:

                        remove_count = node.level - 1

                        if remove_count >= len(package_parts):
                            file_errors.append(
                                f"Invalid relative import: {node.module or ''}"
                            )
                            continue

                        base_parts = (
                            package_parts[:-remove_count]
                            if remove_count
                            else package_parts
                        )

                        target_parts = list(base_parts)

                        if node.module:
                            target_parts.extend(node.module.split("."))

                        base_module = ".".join(target_parts)

                        if node.module and not module_exists(base_module):
                            file_errors.append(
                                f"Relative module not found: {base_module}"
                            )

                        elif not node.module:

                            for alias in node.names:

                                if alias.name == "*":
                                    continue

                                member = (
                                    f"{base_module}.{alias.name}"
                                    if base_module
                                    else alias.name
                                )

                                if not module_exists(member):
                                    file_errors.append(
                                        f"Relative module not found: {member}"
                                    )

                    elif node.module:

                        root = node.module.split(".")[0]

                        if root in {"app", "backend"}:
                            if not module_exists(node.module):
                                file_errors.append(
                                    f"Local module not found: {node.module}"
                                )

            file_errors = list(dict.fromkeys(file_errors))

            if file_errors:
                errors.extend(
                    f"{file_path}: {message}" for message in file_errors
                )
                results.append({
                    "file": file_path,
                    "status": "invalid",
                    "issues": file_errors,
                })
            else:
                results.append({
                    "file": file_path,
                    "status": "valid",
                    "issues": [],
                })

        # Validate package.json.
        package = {}
        dependencies = set()
        package_content = file_map.get("frontend/package.json")

        if package_content is not None:

            try:
                package = json.loads(package_content.lstrip("\ufeff"))

                if not isinstance(package, dict):
                    raise ValueError("package.json must contain a JSON object")

                for dependency_group in (
                    package.get("dependencies", {}),
                    package.get("devDependencies", {}),
                ):
                    if isinstance(dependency_group, dict):
                        dependencies.update(dependency_group.keys())

            except (json.JSONDecodeError, ValueError) as error:
                errors.append(
                    f"frontend/package.json: Invalid package configuration: {error}"
                )
                package = {}

        has_frontend = any(
            path.startswith("frontend/")
            and PurePosixPath(path).suffix.lower() in self.FRONTEND_EXTENSIONS
            for path in file_map
        )

        if has_frontend and package_content is None:
            errors.append(
                "frontend/package.json: Frontend package configuration is missing."
            )

        # Validate frontend imports and external dependencies.
        for file_path, content in file_map.items():

            if (
                PurePosixPath(file_path).suffix.lower()
                not in self.FRONTEND_EXTENSIONS
            ):
                continue

            file_errors = []

            for match in self.IMPORT_PATTERN.finditer(content):

                import_path = match.group(1) or match.group(2)

                if not import_path:
                    continue

                if import_path.startswith("."):

                    source_directory = PurePosixPath(file_path).parent

                    target = posixpath.normpath(
                        posixpath.join(
                            source_directory.as_posix(),
                            import_path,
                        )
                    )

                    candidates = {
                        target,
                        target + ".ts",
                        target + ".tsx",
                        target + ".js",
                        target + ".jsx",
                        target + ".css",
                        target + ".json",
                        posixpath.join(target, "index.ts"),
                        posixpath.join(target, "index.tsx"),
                        posixpath.join(target, "index.js"),
                        posixpath.join(target, "index.jsx"),
                    }

                    if not any(
                        candidate.lower() in normalized_paths
                        for candidate in candidates
                    ):
                        file_errors.append(
                            f"Frontend import not found: {import_path}"
                        )

                else:

                    if (
                        import_path.startswith("@/")
                        or import_path.startswith("#")
                    ):
                        continue

                    package_name = import_path.split("/")[0]

                    if package_name.startswith("@"):
                        segments = import_path.split("/")
                        package_name = "/".join(segments[:2])

                    if package_name in self.NODE_BUILTINS:
                        continue

                    if package_name not in dependencies:
                        file_errors.append(
                            "Frontend dependency missing from package.json: "
                            f"{package_name}"
                        )

            file_errors = list(dict.fromkeys(file_errors))

            if file_errors:
                errors.extend(
                    f"{file_path}: {message}" for message in file_errors
                )
                results.append({
                    "file": file_path,
                    "status": "invalid",
                    "issues": file_errors,
                })
            else:
                results.append({
                    "file": file_path,
                    "status": "valid",
                    "issues": [],
                })

        # Validate all JSON files. Accept UTF-8 BOM.
        for file_path, content in file_map.items():

            if not file_path.lower().endswith(".json"):
                continue

            try:
                json.loads(content.lstrip("\ufeff"))
                results.append({
                    "file": file_path,
                    "status": "valid",
                    "issues": [],
                })

            except json.JSONDecodeError as error:
                message = (
                    f"Invalid JSON at line {error.lineno}, "
                    f"column {error.colno}: {error.msg}"
                )
                errors.append(f"{file_path}: {message}")
                results.append({
                    "file": file_path,
                    "status": "invalid",
                    "issues": [message],
                })

        # Validate required frontend entry files.
        if has_frontend:

            scripts = package.get("scripts", {})
            uses_create_react_app = (
                "react-scripts" in dependencies
                or (
                    isinstance(scripts, dict)
                    and any(
                        isinstance(value, str)
                        and "react-scripts" in value
                        for value in scripts.values()
                    )
                )
            )

            if uses_create_react_app:

                required_files = ["frontend/public/index.html"]

                cra_entrypoints = [
                    "frontend/src/index.js",
                    "frontend/src/index.jsx",
                    "frontend/src/index.ts",
                    "frontend/src/index.tsx",
                ]

                if not any(path in file_map for path in cra_entrypoints):
                    errors.append(
                        "frontend/src/index.tsx: Create React App entrypoint "
                        "is missing. Expected src/index.js, index.jsx, "
                        "index.ts, or index.tsx."
                    )

            else:

                required_files = []

                vite_entrypoints = [
                    "frontend/index.html",
                    "frontend/src/main.js",
                    "frontend/src/main.jsx",
                    "frontend/src/main.ts",
                    "frontend/src/main.tsx",
                ]

                if not any(path in file_map for path in vite_entrypoints):
                    errors.append("Frontend Vite entrypoint is missing.")

            for required_path in required_files:

                if required_path not in file_map:
                    errors.append(
                        f"{required_path}: Required frontend file is missing."
                    )

        # Validate React Router routes when an App component uses React Router.
        app_candidates = [
            "frontend/src/App.tsx",
            "frontend/src/App.ts",
            "frontend/src/App.jsx",
            "frontend/src/App.js",
        ]

        app_path = next(
            (path for path in app_candidates if path in file_map),
            None
        )

        if app_path:

            app_content = file_map[app_path]

            uses_react_router = (
                "react-router-dom" in app_content
                or bool(re.search(r"<(?:Route|Switch|Redirect)\b", app_content))
            )

            if uses_react_router:

                route_pattern = re.compile(r"<Route\b([^>]*)>", re.DOTALL)
                route_matches = list(route_pattern.finditer(app_content))
                routes = []

                for match in route_matches:
                    attributes = match.group(1)

                    path_match = re.search(
                        r"""\bpath\s*=\s*(['"])(.*?)\1""",
                        attributes,
                        re.DOTALL
                    )

                    exact = bool(re.search(r"\bexact\b", attributes))

                    routes.append({
                        "path": path_match.group(2) if path_match else None,
                        "exact": exact,
                        "position": match.start(),
                    })

                has_home_route = any(
                    route["path"] == "/"
                    for route in routes
                )

                has_home_redirect = bool(re.search(
                    r"""<Redirect\b[^>]*\bfrom\s*=\s*(['"])/\1""",
                    app_content
                ))

                if not has_home_route and not has_home_redirect:
                    errors.append(
                        f"{app_path}: React Router homepage route '/' is missing. "
                        "The root URL currently renders no page. Add a homepage "
                        "route or redirect '/' to an existing page."
                    )

                has_fallback = any(
                    route["path"] == "*"
                    or route["path"] is None
                    for route in routes
                )

                if not has_fallback:
                    errors.append(
                        f"{app_path}: React Router fallback route is missing. "
                        "Add a final fallback route for unknown URLs."
                    )

                # In React Router v5, an earlier broad route can shadow
                # a later nested route unless the broad route is exact.
                for index, route in enumerate(routes):

                    broad_path = route["path"]

                    if not broad_path or broad_path in {"/", "*"}:
                        continue

                    if route["exact"]:
                        continue

                    for later_route in routes[index + 1:]:

                        nested_path = later_route["path"]

                        if (
                            nested_path
                            and nested_path != broad_path
                            and nested_path.startswith(
                                broad_path.rstrip("/") + "/"
                            )
                        ):
                            errors.append(
                                f"{app_path}: Route '{broad_path}' needs the "
                                f"exact attribute because it appears before "
                                f"nested route '{nested_path}' and can shadow it."
                            )
                            break

        # Final result.
        errors = list(dict.fromkeys(errors))
        warnings = list(dict.fromkeys(warnings))

        return {
            "generation_id": generation.id,
            "overall_status": "failed" if errors else "passed",
            "total_files": len(file_map),
            "errors": errors,
            "warnings": warnings,
            "file_results": results,
        }


project_validator = ProjectStructureValidator()
