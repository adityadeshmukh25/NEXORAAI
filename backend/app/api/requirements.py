
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.requirement_analysis import RequirementAnalysis
from app.schemas.requirements import (
    RequirementAnalysisRequest,
    RequirementAnalysisResponse
)
from app.services.requirement_agent import requirement_agent

router = APIRouter(tags=["Requirement Analysis"])


@router.post(
    "/requirements/analyze",
    response_model=RequirementAnalysisResponse
)
async def analyze_requirements(
    request: RequirementAnalysisRequest,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == request.project_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    try:
        result = await requirement_agent.analyze(
            request.requirements
        )

        analysis = RequirementAnalysis(
            project_id=request.project_id,
            original_requirements=request.requirements,
            analysis_result=result.model_dump()
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return analysis

    except (RuntimeError, ValueError) as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unexpected error during requirement analysis."
        )


@router.get(
    "/requirements/{analysis_id}",
    response_model=RequirementAnalysisResponse
)
def get_requirement_analysis(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    analysis = db.query(RequirementAnalysis).filter(
        RequirementAnalysis.id == analysis_id
    ).first()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Requirement analysis not found"
        )

    return analysis


@router.get(
    "/projects/{project_id}/requirements",
    response_model=list[RequirementAnalysisResponse]
)
def get_project_requirement_history(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return (
        db.query(RequirementAnalysis)
        .filter(RequirementAnalysis.project_id == project_id)
        .order_by(RequirementAnalysis.created_at.desc())
        .all()
    )
