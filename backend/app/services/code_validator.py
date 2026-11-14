
import ast
from pathlib import Path


class CodeValidator:

    DANGEROUS_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
    }

    DANGEROUS_MODULES = {
        "subprocess",
        "socket",
        "ctypes",
        "multiprocessing",
    }

    def validate_generation(self, generation):

        results = []
        errors = []
        warnings = []

        generated_files = generation.generated_files or []

        for file_data in generated_files:

            file_path = file_data.get("path", "")
            content = file_data.get("content", "")

            if not file_path:
                errors.append("Generated file has no path.")
                continue

            if not isinstance(content, str):
                errors.append(f"Invalid content in {file_path}")
                continue

            extension = Path(file_path).suffix.lower()

            if extension != ".py":
                results.append({
                    "file": file_path,
                    "status": "skipped",
                    "message": "Python syntax validation not applicable."
                })
                continue

            try:
                tree = ast.parse(content, filename=file_path)

            except SyntaxError as error:
                message = (
                    f"{file_path}: Line {error.lineno}: {error.msg}"
                )
                errors.append(message)

                results.append({
                    "file": file_path,
                    "status": "invalid",
                    "message": message
                })
                continue

            file_warnings = []

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in self.DANGEROUS_MODULES:
                            file_warnings.append(
                                f"Potentially risky import: {alias.name}"
                            )

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""

                    if module.split(".")[0] in self.DANGEROUS_MODULES:
                        file_warnings.append(
                            f"Potentially risky import: {module}"
                        )

                elif isinstance(node, ast.Call):

                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.DANGEROUS_CALLS:
                            file_warnings.append(
                                f"Potentially dangerous call: {node.func.id}()"
                            )

                    elif isinstance(node.func, ast.Attribute):

                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "os"
                            and node.func.attr == "system"
                        ):
                            file_warnings.append(
                                "Potentially dangerous call: os.system()"
                            )

                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "subprocess"
                            and node.func.attr in {
                                "run", "Popen", "call", "check_output"
                            }
                        ):
                            file_warnings.append(
                                f"Potentially dangerous call: "
                                f"subprocess.{node.func.attr}()"
                            )

            file_warnings = list(dict.fromkeys(file_warnings))

            if file_warnings:
                for warning in file_warnings:
                    warnings.append(f"{file_path}: {warning}")

                results.append({
                    "file": file_path,
                    "status": "warning",
                    "message": file_warnings
                })
            else:
                results.append({
                    "file": file_path,
                    "status": "valid",
                    "message": "Python syntax is valid. No flagged operations detected."
                })

        return {
            "generation_id": generation.id,
            "overall_status": (
                "failed" if errors else
                "passed_with_warnings" if warnings else
                "passed"
            ),
            "total_files": len(generated_files),
            "errors": errors,
            "warnings": warnings,
            "file_results": results
        }


code_validator = CodeValidator()
