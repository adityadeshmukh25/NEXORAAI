from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.code_generation import CodeGeneration
from app.models.repair_history import RepairHistory

from app.services.autonomous_repair_service import (
    autonomous_repair_service,
)


router = APIRouter(
    prefix="/repairs",
    tags=["Autonomous Repair"],
)


@router.post("/{generation_id}/run")
async def run_autonomous_repair(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found.",
        )

    if generation.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed code generations can be repaired.",
        )

    result = await autonomous_repair_service.run_repair(
        generation=generation,
        db=db,
    )

    return {
        "repair_id": result.id,
        "generation_id": result.generation_id,
        "status": result.status,
        "attempts": result.attempts,
        "initial_errors": result.initial_errors,
        "attempt_details": result.attempt_details,
        "summary": result.summary,
        "created_at": result.created_at,
        "completed_at": result.completed_at,
    }


@router.get("/{generation_id}/history")
def get_repair_history(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found.",
        )

    records = db.query(RepairHistory).filter(
        RepairHistory.generation_id == generation_id
    ).order_by(
        RepairHistory.created_at.desc()
    ).all()

    return [
        {
            "repair_id": record.id,
            "generation_id": record.generation_id,
            "status": record.status,
            "attempts": record.attempts,
            "initial_errors": record.initial_errors,
            "attempt_details": record.attempt_details,
            "summary": record.summary,
            "created_at": record.created_at,
            "completed_at": record.completed_at,
        }
        for record in records
    ]


@router.get("/history/{repair_id}")
def get_repair_record(
    repair_id: int,
    db: Session = Depends(get_db),
):

    record = db.query(RepairHistory).filter(
        RepairHistory.id == repair_id
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Repair history record not found.",
        )

    return {
        "repair_id": record.id,
        "generation_id": record.generation_id,
        "status": record.status,
        "attempts": record.attempts,
        "initial_errors": record.initial_errors,
        "attempt_details": record.attempt_details,
        "summary": record.summary,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
    }