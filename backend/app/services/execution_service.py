import ast
import time

from pathlib import Path


MAX_OUTPUT_LENGTH = 20000


class ExecutionService:

    @staticmethod
    def get_generation_path(
        project_id: int,
        generation_id: int,
    ) -> Path:

        base_path = (
            Path(__file__).resolve().parents[2]
            / "generated_projects"
        ).resolve()

        generation_path = (
            base_path
            / f"project_{project_id}"
            / f"generation_{generation_id}"
        ).resolve()

        if not generation_path.is_relative_to(base_path):
            raise ValueError("Invalid generation directory")

        if not generation_path.exists():
            raise FileNotFoundError(
                "Generated project directory not found"
            )

        return generation_path

    @staticmethod
    def compile_python(
        project_id: int,
        generation_id: int,
        timeout_seconds: int = 30,
    ) -> dict:

        start_time = time.time()

        try:
            generation_path = (
                ExecutionService.get_generation_path(
                    project_id,
                    generation_id,
                )
            )

            backend_path = generation_path / "backend"

            if not backend_path.exists():
                raise FileNotFoundError(
                    "Backend directory not found"
                )

            python_files = list(backend_path.rglob("*.py"))

            if not python_files:
                raise FileNotFoundError(
                    "No Python files found"
                )

            errors = []

            for file_path in python_files:

                if time.time() - start_time > timeout_seconds:
                    return {
                        "status": "timeout",
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": "Compilation timed out",
                        "execution_time": round(
                            time.time() - start_time, 3
                        ),
                    }

                try:
                    source_code = file_path.read_text(
                        encoding="utf-8"
                    )

                    ast.parse(
                        source_code,
                        filename=str(file_path),
                    )

                except SyntaxError as exc:
                    lines = source_code.splitlines()

                    error_line = ""

                    if exc.lineno and 1 <= exc.lineno <= len(lines):
                        error_line = lines[exc.lineno - 1].strip()

                    errors.append(
                        f"File: {file_path.name}\n"
                        f"Line: {exc.lineno}\n"
                        f"Error: {exc.msg}\n"
                        f"Source code: {error_line}"
                    )

            execution_time = round(
                time.time() - start_time, 3
            )

            if errors:
                return {
                    "status": "failed",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "\n".join(errors)[:MAX_OUTPUT_LENGTH],
                    "execution_time": execution_time,
                }

            return {
                "status": "completed",
                "exit_code": 0,
                "stdout": (
                    f"Successfully checked "
                    f"{len(python_files)} Python files."
                ),
                "stderr": "",
                "execution_time": execution_time,
            }

        except Exception as exc:

            return {
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": str(exc)[:MAX_OUTPUT_LENGTH],
                "execution_time": round(
                    time.time() - start_time, 3
                ),
            }