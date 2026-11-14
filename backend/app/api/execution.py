from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.execution import CodeExecution
from app.models.code_generation import CodeGeneration
from app.schemas.execution import (
    CodeExecutionRequest,
    CodeExecutionResponse,
)
from app.services.execution_service import ExecutionService

router = APIRouter(
    prefix="/api/executions",
    tags=["Code Execution"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/{generation_id}/run",
    response_model=CodeExecutionResponse,
)
def run_code(
    generation_id: int,
    request: CodeExecutionRequest,
    db: Session = Depends(get_db),
):
    generation = (
        db.query(CodeGeneration)
        .filter(CodeGeneration.id == generation_id)
        .first()
    )

    if generation is None:
        raise HTTPException(
            status_code=404,
            detail="Code generation not found",
        )

    execution = CodeExecution(
        generation_id=generation_id,
        status="running",
        command=request.operation,
        started_at=datetime.utcnow(),
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    result = ExecutionService.compile_python(
        project_id=generation.project_id,
        generation_id=generation_id,
        timeout_seconds=request.timeout_seconds,
    )

    execution.status = result["status"]
    execution.exit_code = result["exit_code"]
    execution.stdout = result["stdout"]
    execution.stderr = result["stderr"]
    execution.execution_time = result["execution_time"]
    execution.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(execution)

    return execution


@router.get(
    "/{execution_id}",
    response_model=CodeExecutionResponse,
)
def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
):
    execution = (
        db.query(CodeExecution)
        .filter(CodeExecution.id == execution_id)
        .first()
    )

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    return execution

@router.get(
    "/generation/{generation_id}/history",
    response_model=list[CodeExecutionResponse],
)
def get_execution_history(
    generation_id: int,
    db: Session = Depends(get_db),
):
    generation = (
        db.query(CodeGeneration)
        .filter(CodeGeneration.id == generation_id)
        .first()
    )

    if generation is None:
        raise HTTPException(
            status_code=404,
            detail="Code generation not found",
        )

    executions = (
        db.query(CodeExecution)
        .filter(CodeExecution.generation_id == generation_id)
        .order_by(CodeExecution.created_at.desc())
        .all()
    )

    return executions