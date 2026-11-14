
from datetime import datetime
from pathlib import Path
import ast
import os
import tempfile

from sqlalchemy.orm import Session

from app.models.code_generation import CodeGeneration
from app.models.debugging import DebuggingSession
from app.models.execution import CodeExecution
from app.models.code_fix import CodeFix


class CodeFixService:

    @staticmethod
    def get_project_root(db: Session, generation_id: int) -> Path:

        generation = (
            db.query(CodeGeneration)
            .filter(CodeGeneration.id == generation_id)
            .first()
        )

        if generation is None:
            raise ValueError("Code generation record not found")

        backend_dir = Path(__file__).resolve().parents[2]

        project_root = (
            backend_dir
            / "generated_projects"
            / f"project_{generation.project_id}"
            / f"generation_{generation_id}"
        ).resolve()

        if not project_root.is_dir():
            raise ValueError("Generated project directory not found")

        return project_root

    @staticmethod
    def create_fix(
        db: Session,
        debugging_session_id: int,
    ) -> CodeFix:

        debugging = (
            db.query(DebuggingSession)
            .filter(DebuggingSession.id == debugging_session_id)
            .first()
        )

        if debugging is None:
            raise ValueError("Debugging session not found")

        if debugging.status != "completed":
            raise ValueError("Debugging session is not completed")

        if not debugging.corrected_code:
            raise ValueError("No corrected code available")

        execution = (
            db.query(CodeExecution)
            .filter(
                CodeExecution.id == debugging.execution_id,
                CodeExecution.generation_id == debugging.generation_id,
            )
            .first()
        )

        if execution is None:
            raise ValueError("Associated execution record not found")

        project_root = CodeFixService.get_project_root(
            db,
            debugging.generation_id,
        )

        filename = None

        for line in (execution.stderr or "").splitlines():
            if line.strip().startswith("File:"):
                filename = line.split(":", 1)[1].strip()
                break

        if not filename:
            raise ValueError("Source filename not found")

        source_file = None

        for candidate in project_root.rglob(Path(filename).name):
            candidate = candidate.resolve()

            if (
                candidate.is_relative_to(project_root)
                and candidate.is_file()
                and candidate.suffix == ".py"
            ):
                source_file = candidate
                break

        if source_file is None:
            raise ValueError("Original Python source file not found")

        original_code = source_file.read_text(encoding="utf-8")

        if original_code == debugging.corrected_code:
            raise ValueError("Original and corrected code are identical")

        existing_fix = (
            db.query(CodeFix)
            .filter(
                CodeFix.debugging_session_id == debugging_session_id,
                CodeFix.status == "pending",
            )
            .first()
        )

        if existing_fix:
            return existing_fix

        code_fix = CodeFix(
            generation_id=debugging.generation_id,
            debugging_session_id=debugging_session_id,
            file_path=str(source_file.relative_to(project_root)),
            original_code=original_code,
            corrected_code=debugging.corrected_code,
            status="pending",
        )

        db.add(code_fix)
        db.commit()
        db.refresh(code_fix)

        return code_fix

    @staticmethod
    def apply_fix(
        db: Session,
        fix_id: int,
    ) -> CodeFix:

        code_fix = (
            db.query(CodeFix)
            .filter(CodeFix.id == fix_id)
            .with_for_update()
            .first()
        )

        if code_fix is None:
            raise ValueError("Code fix not found")

        if code_fix.status != "approved":
            raise ValueError("Only approved code fixes can be applied")

        project_root = CodeFixService.get_project_root(
            db,
            code_fix.generation_id,
        )

        target_file = (
            project_root / code_fix.file_path
        ).resolve()

        if not target_file.is_relative_to(project_root):
            raise ValueError("Invalid target file path")

        if not target_file.is_file() or target_file.suffix != ".py":
            raise ValueError("Target Python file does not exist")

        current_code = target_file.read_text(encoding="utf-8")

        # Prevent overwriting changes made after the fix was created.
        if current_code != code_fix.original_code:
            raise ValueError(
                "Original file has changed since the fix was created. "
                "Create a new debugging session and review again."
            )

        # Validate corrected Python syntax before applying.
        try:
            ast.parse(code_fix.corrected_code)
        except SyntaxError as exc:
            raise ValueError(
                f"Corrected code contains a syntax error: {exc}"
            ) from exc

        # Create a backup before applying the correction.
        backup_dir = (
            project_root / "backups" / "code_fixes"
        ).resolve()

        if not backup_dir.is_relative_to(project_root):
            raise ValueError("Invalid backup directory")

        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")

        backup_file = backup_dir / f"fix_{fix_id}_{timestamp}.py"

        backup_file.write_text(
            current_code,
            encoding="utf-8",
        )

        # Write corrected code to a temporary file.
        temp_file = target_file.with_name(
            target_file.name + f".fix_{fix_id}.tmp"
        )

        try:
            temp_file.write_text(
                code_fix.corrected_code,
                encoding="utf-8",
            )

            # Atomic replacement on the same filesystem.
            temp_file.replace(target_file)

        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise

        code_fix.backup_path = str(
            backup_file.relative_to(project_root)
        )

        code_fix.status = "applied"
        code_fix.applied_at = datetime.utcnow()

        db.commit()
        db.refresh(code_fix)

        return code_fix

    @staticmethod
    def rollback_fix(
        db: Session,
        fix_id: int,
    ) -> CodeFix:

        fix = (
            db.query(CodeFix)
            .filter(CodeFix.id == fix_id)
            .first()
        )

        if fix is None:
            raise ValueError("Code fix not found")

        if fix.status != "applied":
            raise ValueError("Only applied fixes can be rolled back")

        project_root = CodeFixService.get_project_root(
            db,
            fix.generation_id,
        ).resolve()

        target_file = (
            project_root / fix.file_path
        ).resolve()

        # Prevent paths from escaping the generated project.
        if not target_file.is_relative_to(project_root):
            raise ValueError("Invalid target file path")

        if not target_file.is_file():
            raise ValueError("Target file does not exist")

        if not fix.backup_path:
            raise ValueError("Backup path is missing")

        backup_file = (
            project_root / fix.backup_path
        ).resolve()

        if not backup_file.is_relative_to(project_root):
            raise ValueError("Invalid backup file path")

        if not backup_file.is_file():
            raise ValueError("Backup file does not exist")

        current_code = target_file.read_text(encoding="utf-8")

        # Do not overwrite changes made after the fix was applied.
        if current_code != fix.corrected_code:
            raise ValueError(
                "The target file has changed since the fix was applied. "
                "Rollback cancelled to protect newer changes."
            )

        original_code = backup_file.read_text(encoding="utf-8")

        # Verify backup integrity against the recorded original.
        if original_code != fix.original_code:
            raise ValueError("Backup content does not match original code")

        # Restore the original file, even if its syntax is invalid.
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(target_file.parent),
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(original_code)
                temp_path = temp_file.name

            os.replace(temp_path, target_file)

        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        fix.status = "rolled_back"
        fix.reviewed_at = datetime.utcnow()

        db.commit()
        db.refresh(fix)

        return fix
