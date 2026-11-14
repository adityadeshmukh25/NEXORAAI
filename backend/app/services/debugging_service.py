
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.execution import CodeExecution
from app.models.debugging import DebuggingSession
from app.models.code_generation import CodeGeneration
from app.services.debugging_agent import DebuggingAgent


class DebuggingService:

    @staticmethod
    def debug_execution(
        db: Session,
        generation_id: int,
        execution_id: int,
    ) -> DebuggingSession:

        execution = (
            db.query(CodeExecution)
            .filter(
                CodeExecution.id == execution_id,
                CodeExecution.generation_id == generation_id,
            )
            .first()
        )

        if execution is None:
            raise ValueError("Execution record not found")

        if execution.status == "completed" and execution.exit_code == 0:
            raise ValueError(
                "Execution completed successfully. No error to debug."
            )

        error_message = execution.stderr or ""

        if not error_message.strip():
            error_message = (
                f"Execution failed with exit code "
                f"{execution.exit_code}. "
                f"Command: {execution.command or 'Unknown'}"
            )

        debugging_session = DebuggingSession(
            generation_id=generation_id,
            execution_id=execution_id,
            status="running",
            error_summary="Analyzing error...",
        )

        db.add(debugging_session)
        db.commit()
        db.refresh(debugging_session)

        try:
            generation = (
                db.query(CodeGeneration)
                .filter(CodeGeneration.id == generation_id)
                .first()
            )

            if generation is None:
                raise ValueError("Code generation record not found")

            # Resolve generated project directory.
            backend_dir = Path(__file__).resolve().parents[2]
            project_root = (
                backend_dir
                / "generated_projects"
                / f"project_{generation.project_id}"
                / f"generation_{generation_id}"
            ).resolve()

            # Extract filename from execution error.
            source_file = None

            for line in error_message.splitlines():
                if line.strip().startswith("File:"):
                    filename = line.split(":", 1)[1].strip()

                    # Search inside the generation directory and its subdirectories.
                    for candidate in project_root.rglob(filename):

                        candidate = candidate.resolve()

                        if not candidate.is_relative_to(project_root):
                            continue

                        if candidate.is_file() and candidate.suffix == ".py":
                            source_file = candidate
                            break

            source_code = ""

            if source_file:
                source_code = source_file.read_text(
                    encoding="utf-8"
                )

            agent = DebuggingAgent()

            analysis = agent.analyze_error(
                error_message,
                source_code,
            )

            debugging_session.error_summary = analysis["error_summary"]
            debugging_session.root_cause = analysis["root_cause"]
            debugging_session.suggested_fix = analysis["suggested_fix"]
            debugging_session.corrected_code = analysis["corrected_code"]
            debugging_session.status = "completed"

        except Exception as exc:
            debugging_session.status = "failed"
            debugging_session.root_cause = str(exc)

        debugging_session.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(debugging_session)

        return debugging_session
