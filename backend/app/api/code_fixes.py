
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.code_fix import CodeFix
from app.schemas.code_fix import (
    CodeFixResponse,
    CodeFixReviewRequest,
)
from app.services.code_fix_service import CodeFixService


router = APIRouter(
    prefix="/api/code-fixes",
    tags=["Code Fix Approval"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create a proposed fix from a debugging session
@router.post(
    "/debugging/{debugging_session_id}",
    response_model=CodeFixResponse,
)
def create_code_fix(
    debugging_session_id: int,
    db: Session = Depends(get_db),
):
    try:
        return CodeFixService.create_fix(
            db,
            debugging_session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# Get all fixes for a generation
@router.get(
    "/generation/{generation_id}",
    response_model=list[CodeFixResponse],
)
def get_generation_fixes(
    generation_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(CodeFix)
        .filter(CodeFix.generation_id == generation_id)
        .order_by(CodeFix.created_at.desc())
        .all()
    )


# Get one proposed fix
@router.get(
    "/{fix_id}",
    response_model=CodeFixResponse,
)
def get_code_fix(
    fix_id: int,
    db: Session = Depends(get_db),
):
    code_fix = (
        db.query(CodeFix)
        .filter(CodeFix.id == fix_id)
        .first()
    )

    if code_fix is None:
        raise HTTPException(
            status_code=404,
            detail="Code fix not found",
        )

    return code_fix


# Approve or reject a proposed fix
@router.post(
    "/{fix_id}/review",
    response_model=CodeFixResponse,
)
def review_code_fix(
    fix_id: int,
    review: CodeFixReviewRequest,
    db: Session = Depends(get_db),
):
    code_fix = (
        db.query(CodeFix)
        .filter(CodeFix.id == fix_id)
        .first()
    )

    if code_fix is None:
        raise HTTPException(
            status_code=404,
            detail="Code fix not found",
        )

    if code_fix.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Code fix has already been {code_fix.status}",
        )

    if review.action == "approve":
        code_fix.status = "approved"
        code_fix.rejection_reason = None

    elif review.action == "reject":
        code_fix.status = "rejected"
        code_fix.rejection_reason = (
            review.rejection_reason or "Rejected by reviewer"
        )

    code_fix.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(code_fix)

    return code_fix


# Apply an approved code correction
@router.post(
    "/{fix_id}/apply",
    response_model=CodeFixResponse,
)
def apply_code_fix(
    fix_id: int,
    db: Session = Depends(get_db),
):
    try:
        return CodeFixService.apply_fix(
            db,
            fix_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/{fix_id}/rollback",
    response_model=CodeFixResponse,
)
def rollback_code_fix(
    fix_id: int,
    db: Session = Depends(get_db),
):
    try:
        return CodeFixService.rollback_fix(db, fix_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
