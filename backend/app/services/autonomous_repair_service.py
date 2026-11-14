import ast
import json

from datetime import datetime
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from app.models.code_generation import CodeGeneration
from app.models.repair_history import RepairHistory

from app.services.project_validator import project_validator
from app.services.repair_agent import repair_agent
from app.services.project_context_analyzer import project_context_analyzer
from app.services.transactional_file_writer import transactional_file_writer


ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".css",
    ".json", ".html", ".md", ".txt", ".toml",
    ".yaml", ".yml", ".sql",
}

EXCLUDED_DIRECTORIES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
}

MAX_ATTEMPTS = 3


class AutonomousRepairService:

    def __init__(self):
        self.backend_root = Path(__file__).resolve().parents[2]
        self.generated_root = self.backend_root / "generated_projects"
        self.backup_root = self.backend_root / "repair_backups"

    def get_workspace(self, generation):
        workspace = (
            self.generated_root
            / f"project_{generation.project_id}"
            / f"generation_{generation.id}"
        )
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace.resolve()

    def safe_path(self, workspace, relative_path):
        if not isinstance(relative_path, str):
            raise ValueError("Invalid file path.")

        normalized = relative_path.replace("\\", "/").strip()
        relative = PurePosixPath(normalized)
        windows_relative = Path(relative_path)

        if (
            not normalized
            or relative.is_absolute()
            or windows_relative.is_absolute()
            or ".." in relative.parts
            or ".." in windows_relative.parts
            or ":" in normalized
            or not relative.parts
        ):
            raise ValueError(f"Unsafe file path: {relative_path}")

        if relative.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension is not allowed: {relative.suffix}"
            )

        root = workspace.resolve()
        target = root.joinpath(*relative.parts)
        current = root

        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(
                    f"Symbolic links are not allowed: {relative_path}"
                )

        try:
            target.resolve(strict=False).relative_to(root)
        except ValueError as error:
            raise ValueError(
                "File path is outside the project workspace."
            ) from error

        return target

    @staticmethod
    def read_text(path):
        # utf-8-sig removes a leading UTF-8 BOM when one is present.
        return path.read_text(encoding="utf-8-sig", errors="replace")

    def collect_project_files(self, generation, workspace):
        files = {}

        for item in generation.generated_files or []:
            if not isinstance(item, dict):
                continue

            raw_path = item.get("path")
            if not isinstance(raw_path, str) or not raw_path:
                continue

            relative_path = PurePosixPath(
                raw_path.replace("\\", "/")
            ).as_posix()

            target = self.safe_path(workspace, relative_path)
            content = item.get("content", "")

            if target.is_file():
                content = self.read_text(target)

            if isinstance(content, str):
                files[relative_path] = content.lstrip("\ufeff")

        for target in workspace.rglob("*"):
            if not target.is_file() or target.is_symlink():
                continue

            relative = target.relative_to(workspace)

            if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
                continue
            if target.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            if not target.resolve().is_relative_to(workspace):
                continue

            relative_path = relative.as_posix()
            if relative_path not in files:
                files[relative_path] = self.read_text(target).lstrip("\ufeff")

        return files

    def validate_project(self, generation, workspace):
        result = project_validator.validate_generation(generation)
        errors = list(result.get("errors", []))
        files = self.collect_project_files(generation, workspace)

        for relative_path, content in files.items():
            if relative_path.endswith(".py"):
                try:
                    ast.parse(content, filename=relative_path)
                except SyntaxError as error:
                    errors.append(
                        f"{relative_path}: Python syntax error "
                        f"at line {error.lineno}, "
                        f"column {error.offset}: {error.msg}"
                    )

            elif relative_path.lower().endswith(".json"):
                try:
                    json.loads(content.lstrip("\ufeff"))
                except json.JSONDecodeError as error:
                    errors.append(
                        f"{relative_path}: JSON error "
                        f"at line {error.lineno}, "
                        f"column {error.colno}: {error.msg}"
                    )

        errors = list(dict.fromkeys(errors))
        return {
            "passed": not errors,
            "errors": errors,
            "total_files": len(files),
        }

    def validate_repair_files(self, proposed_files, workspace, current_files):
        if not isinstance(proposed_files, list) or not proposed_files:
            raise ValueError("Repair agent returned no files.")

        validated = {}
        seen = set()
        normalized_current = {
            PurePosixPath(path.replace("\\", "/")).as_posix()
            for path in current_files
        }

        for item in proposed_files:
            if not isinstance(item, dict):
                raise ValueError("Invalid repair file entry.")

            raw_path = item.get("path")
            action = item.get("action")
            content = item.get("content")

            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("Repair file path is missing.")

            relative_path = PurePosixPath(
                raw_path.replace("\\", "/").strip()
            ).as_posix()

            if relative_path in seen:
                raise ValueError(f"Duplicate repair path: {relative_path}")
            seen.add(relative_path)

            if action not in {"create", "update", "delete"}:
                raise ValueError(f"Invalid action for {relative_path}.")

            target = self.safe_path(workspace, relative_path)
            exists = target.is_file()

            if target.exists() and not exists:
                raise ValueError(
                    f"Target is not a regular file: {relative_path}"
                )

            if action == "create":
                if exists or relative_path in normalized_current:
                    raise ValueError(
                        f"Cannot create existing file: {relative_path}"
                    )

            elif action == "update":
                if not exists:
                    raise ValueError(
                        f"Cannot update missing file: {relative_path}"
                    )
                if relative_path not in normalized_current:
                    raise ValueError(
                        f"Cannot update an uninspected file: {relative_path}"
                    )

            elif action == "delete":
                if not exists:
                    raise ValueError(
                        f"Cannot delete missing file: {relative_path}"
                    )
                if relative_path not in normalized_current:
                    raise ValueError(
                        f"Cannot delete an uninspected file: {relative_path}"
                    )
                validated[relative_path] = {
                    "action": "delete",
                    "content": None,
                }
                continue

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Empty or invalid content for {relative_path}."
                )

            if relative_path.endswith(".py"):
                try:
                    ast.parse(content, filename=relative_path)
                except SyntaxError as error:
                    raise ValueError(
                        f"Invalid Python in {relative_path}: "
                        f"line {error.lineno}, "
                        f"column {error.offset}: {error.msg}"
                    ) from error

            if relative_path.lower().endswith(".json"):
                try:
                    json.loads(content.lstrip("\ufeff"))
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSON in {relative_path}: "
                        f"line {error.lineno}, "
                        f"column {error.colno}: {error.msg}"
                    ) from error

            validated[relative_path] = {
                "action": action,
                "content": content,
            }

        if not validated:
            raise ValueError("No valid repair operations were proposed.")

        return validated

    def synchronize_generated_files(self, generation, validated_files):
        existing_items = {}

        for item in generation.generated_files or []:
            if not isinstance(item, dict):
                continue

            path = item.get("path")
            if isinstance(path, str):
                normalized = PurePosixPath(
                    path.replace("\\", "/")
                ).as_posix()
                existing_items[normalized] = dict(item)

        updated_files = []

        for relative_path, item in existing_items.items():
            change = validated_files.get(relative_path)

            if change is None:
                updated_files.append(item)
                continue
            if change["action"] == "delete":
                continue

            item["content"] = change["content"]
            updated_files.append(item)

        for relative_path, change in validated_files.items():
            if change["action"] != "create":
                continue

            extension = Path(relative_path).suffix.lower()
            language = {
                ".py": "python",
                ".tsx": "typescript",
                ".ts": "typescript",
                ".jsx": "javascript",
                ".js": "javascript",
                ".css": "css",
                ".json": "json",
                ".html": "html",
            }.get(extension, "text")

            updated_files.append({
                "path": relative_path,
                "content": change["content"],
                "language": language,
                "description": "Created by autonomous repair agent",
            })

        generation.generated_files = updated_files

    def apply_repair_files(
        self, generation, workspace, current_files,
        validated_files, repair_id, attempt,
    ):
        backup_directory = (
            self.backup_root
            / f"project_{generation.project_id}"
            / f"generation_{generation.id}"
            / f"repair_{repair_id}"
            / f"attempt_{attempt}"
        )

        changes_to_apply = []

        for relative_path, item in validated_files.items():
            target = self.safe_path(workspace, relative_path)
            action = item["action"]

            if action in {"update", "delete"}:
                if not target.is_file():
                    raise RuntimeError(
                        f"File disappeared before repair: {relative_path}"
                    )

                disk_content = self.read_text(target).lstrip("\ufeff")
                if disk_content != current_files.get(relative_path):
                    raise RuntimeError(
                        f"File changed after inspection: {relative_path}"
                    )

            elif target.exists():
                raise RuntimeError(
                    f"New file already exists: {relative_path}"
                )

            changes_to_apply.append({
                "path": relative_path,
                "action": action,
                "content": item["content"],
            })

        applied_changes = transactional_file_writer.apply(
            workspace=workspace,
            backup_directory=backup_directory,
            changes=changes_to_apply,
        )

        try:
            self.synchronize_generated_files(generation, validated_files)
        except Exception:
            transactional_file_writer.rollback(workspace, applied_changes)
            raise

        return applied_changes

    def history_safe_changes(self, changes):
        result = []
        for change in changes:
            item = dict(change)
            backup = item.get("backup")
            if backup:
                try:
                    item["backup"] = str(
                        Path(backup).relative_to(self.backend_root)
                    )
                except ValueError:
                    item["backup"] = str(backup)
            result.append(item)
        return result

    def record_attempt(self, history, db, details):
        attempt_details = list(history.attempt_details or [])
        attempt_details.append(details)
        history.attempt_details = attempt_details
        db.commit()
        db.refresh(history)

    async def run_repair(self, generation: CodeGeneration, db: Session):
        workspace = self.get_workspace(generation)
        initial_validation = self.validate_project(generation, workspace)

        history = RepairHistory(
            generation_id=generation.id,
            status="running",
            attempts=0,
            initial_errors=initial_validation["errors"],
            attempt_details=[],
            summary="Autonomous repair started.",
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        if initial_validation["passed"]:
            history.status = "no_changes_needed"
            history.summary = (
                "Project passed validation. No repair was needed."
            )
            history.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(history)
            return history

        for attempt in range(1, MAX_ATTEMPTS + 1):
            history.attempts = attempt
            db.commit()

            current_changes = []
            changes_applied = False
            db_changes_committed = False

            try:
                db.refresh(generation)
                current_files = self.collect_project_files(generation, workspace)
                validation = self.validate_project(generation, workspace)

                if validation["passed"]:
                    break

                project_context = project_context_analyzer.analyze(current_files)
                repair_result = await repair_agent.repair(
                    errors=validation["errors"],
                    project_files=current_files,
                    attempt=attempt,
                    context=project_context,
                )

                validated_files = self.validate_repair_files(
                    proposed_files=repair_result["files"],
                    workspace=workspace,
                    current_files=current_files,
                )

                current_changes = self.apply_repair_files(
                    generation=generation,
                    workspace=workspace,
                    current_files=current_files,
                    validated_files=validated_files,
                    repair_id=history.id,
                    attempt=attempt,
                )
                changes_applied = True

                try:
                    db.commit()
                    db_changes_committed = True
                    changes_applied = False
                except Exception:
                    db.rollback()
                    transactional_file_writer.rollback(workspace, current_changes)
                    changes_applied = False
                    current_changes = []
                    db.refresh(generation)
                    raise

                post_validation = self.validate_project(generation, workspace)
                details = {
                    "attempt": attempt,
                    "status": (
                        "passed" if post_validation["passed"]
                        else "validation_failed"
                    ),
                    "errors_before_repair": validation["errors"],
                    "errors_after_repair": post_validation["errors"],
                    "summary": repair_result.get(
                        "summary", "Repair proposed and applied."
                    ),
                    "root_causes": repair_result.get("root_causes", []),
                    "changes": self.history_safe_changes(current_changes),
                }

                history = db.query(RepairHistory).filter(
                    RepairHistory.id == history.id
                ).first()
                self.record_attempt(history, db, details)

                if post_validation["passed"]:
                    break

            except Exception as error:
                if changes_applied and current_changes:
                    try:
                        transactional_file_writer.rollback(
                            workspace, current_changes
                        )
                    except Exception as rollback_error:
                        error = RuntimeError(
                            f"{error}; rollback failed: {rollback_error}"
                        )

                db.rollback()
                db.refresh(generation)
                history = db.query(RepairHistory).filter(
                    RepairHistory.id == history.id
                ).first()

                if history is None:
                    raise RuntimeError(
                        "Repair history record disappeared."
                    )

                failure_details = {
                    "attempt": attempt,
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                    "changes_applied": db_changes_committed,
                }
                attempt_details = list(history.attempt_details or [])
                attempt_details.append(failure_details)
                history.attempt_details = attempt_details
                history.attempts = attempt
                history.summary = f"Attempt {attempt} failed: {error}"
                db.commit()
                db.refresh(history)

        db.refresh(generation)
        final_validation = self.validate_project(generation, workspace)
        history = db.query(RepairHistory).filter(
            RepairHistory.id == history.id
        ).first()

        if history is None:
            raise RuntimeError("Repair history record disappeared.")

        if final_validation["passed"]:
            history.status = "completed"
            history.summary = (
                "Autonomous repair completed. The project passed "
                "available structure, Python syntax and JSON validation."
            )
        else:
            history.status = "failed"
            history.summary = (
                "Repair attempts finished, but validation errors remain."
            )
            attempt_details = list(history.attempt_details or [])
            attempt_details.append({
                "final_validation_errors": final_validation["errors"]
            })
            history.attempt_details = attempt_details

        history.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(history)
        return history


autonomous_repair_service = AutonomousRepairService()
