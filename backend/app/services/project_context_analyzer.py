
import ast
import json
import re
from pathlib import PurePosixPath
from typing import Any


class ProjectContextAnalyzer:

    EXCLUDED_DIRS = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
    }

    FRONTEND_EXTENSIONS = {
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
    }

    def analyze(
        self,
        project_files: dict[str, str],
    ) -> dict[str, Any]:

        paths = set(project_files.keys())

        return {
            "project_structure": self._build_structure(paths),
            "python_dependencies": self._analyze_python(
                project_files,
                paths,
            ),
            "frontend_dependencies": self._analyze_frontend(
                project_files,
                paths,
            ),
            "package_dependencies": self._analyze_package_json(
                project_files,
            ),
            "file_count": len(paths),
        }

    def _build_structure(self, paths: set[str]) -> list[str]:

        return sorted(
            path
            for path in paths
            if not any(
                part in self.EXCLUDED_DIRS
                for part in PurePosixPath(path).parts
            )
        )

    def _resolve_python_module(
        self,
        source_path: str,
        module: str,
        level: int,
    ) -> str | None:

        parts = list(
            PurePosixPath(source_path).parent.parts
        )

        for _ in range(max(level - 1, 0)):
            if parts:
                parts.pop()

        if module:
            parts.extend(module.split("."))

        return "/".join(parts) if parts else None

    def _module_exists(
        self,
        module_path: str,
        paths: set[str],
    ) -> bool:

        candidates = {
            module_path + ".py",
            module_path + "/__init__.py",
        }

        return any(
            candidate in paths
            for candidate in candidates
        )

    def _analyze_python(
        self,
        project_files: dict[str, str],
        paths: set[str],
    ) -> list[dict[str, Any]]:

        results = []

        for path, content in project_files.items():

            if not path.endswith(".py"):
                continue

            try:
                tree = ast.parse(
                    content,
                    filename=path,
                )
            except SyntaxError as error:
                results.append({
                    "file": path,
                    "error": (
                        f"Syntax error at line {error.lineno}, "
                        f"column {error.offset}: {error.msg}"
                    ),
                })
                continue

            imports = []

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):

                    for alias in node.names:
                        imports.append({
                            "module": alias.name,
                            "relative": False,
                        })

                elif isinstance(node, ast.ImportFrom):

                    module_path = self._resolve_python_module(
                        path,
                        node.module or "",
                        node.level,
                    )

                    if node.level:

                        exists = (
                            module_path is not None
                            and self._module_exists(
                                module_path,
                                paths,
                            )
                        )

                        imports.append({
                            "module": module_path,
                            "relative": True,
                            "exists": exists,
                        })

            results.append({
                "file": path,
                "imports": imports,
            })

        return results

    def _analyze_frontend(
        self,
        project_files: dict[str, str],
        paths: set[str],
    ) -> list[dict[str, Any]]:

        results = []

        import_pattern = re.compile(
            r"""(?:from\s+|import\s*\()\s*["']([^"']+)["']"""
        )

        for path, content in project_files.items():

            suffix = PurePosixPath(path).suffix

            if suffix not in self.FRONTEND_EXTENSIONS:
                continue

            imports = []

            for match in import_pattern.finditer(content):

                module = match.group(1)

                if not module.startswith("."):
                    imports.append({
                        "module": module,
                        "type": "external",
                    })
                    continue

                base = PurePosixPath(path).parent
                resolved = str(base.joinpath(module))

                candidates = {
                    resolved,
                    resolved + ".ts",
                    resolved + ".tsx",
                    resolved + ".js",
                    resolved + ".jsx",
                    resolved + ".css",
                    resolved + "/index.ts",
                    resolved + "/index.tsx",
                    resolved + "/index.js",
                    resolved + "/index.jsx",
                }

                exists = any(
                    candidate in paths
                    for candidate in candidates
                )

                imports.append({
                    "module": module,
                    "type": "local",
                    "exists": exists,
                })

            results.append({
                "file": path,
                "imports": imports,
            })

        return results

    def _analyze_package_json(
        self,
        project_files: dict[str, str],
    ) -> dict[str, Any]:

        package_content = project_files.get(
            "frontend/package.json"
        )

        if not package_content:
            return {
                "found": False,
                "dependencies": [],
                "dev_dependencies": [],
                "error": "frontend/package.json is missing",
            }

        try:
            package = json.loads(package_content)

        except json.JSONDecodeError as error:
            return {
                "found": True,
                "dependencies": [],
                "dev_dependencies": [],
                "error": f"Invalid package.json: {error}",
            }

        return {
            "found": True,
            "dependencies": sorted(
                package.get("dependencies", {}).keys()
            ),
            "dev_dependencies": sorted(
                package.get("devDependencies", {}).keys()
            ),
            "scripts": package.get("scripts", {}),
            "error": None,
        }


project_context_analyzer = ProjectContextAnalyzer()
