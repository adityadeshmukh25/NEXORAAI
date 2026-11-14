from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.debugging import DebuggingSession
from app.schemas.debugging import (
    DebuggingRequest,
    DebuggingResponse,
)
from app.services.debugging_service import DebuggingService


router = APIRouter(
    prefix="/api/debugging",
    tags=["AI Debugging"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/analyze",
    response_model=DebuggingResponse,
)
def analyze_execution_error(
    request: DebuggingRequest,
    db: Session = Depends(get_db),
):
    if request.execution_id is None:
        raise HTTPException(
            status_code=400,
            detail="execution_id is required",
        )

    try:
        return DebuggingService.debug_execution(
            db=db,
            generation_id=request.generation_id,
            execution_id=request.execution_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Debugging failed: {str(exc)}",
        )


@router.get(
    "/{debugging_id}",
    response_model=DebuggingResponse,
)
def get_debugging_result(
    debugging_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(DebuggingSession)
        .filter(DebuggingSession.id == debugging_id)
        .first()
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Debugging session not found",
        )

    return result