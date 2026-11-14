from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.requirement_analysis import RequirementAnalysis
from app.models.architecture_plan import ArchitecturePlan
from app.schemas.architecture import (
    ArchitecturePlanRequest,
    ArchitecturePlanResponse
)
from app.services.architecture_agent import architecture_agent


router = APIRouter(
    prefix="/architecture",
    tags=["Architecture Planning"]
)


@router.post("/generate", response_model=ArchitecturePlanResponse)
async def generate_architecture(
    request: ArchitecturePlanRequest,
    db: Session = Depends(get_db)
):
    requirement = db.query(RequirementAnalysis).filter(
        RequirementAnalysis.id == request.requirement_analysis_id
    ).first()

    if not requirement:
        raise HTTPException(
            status_code=404,
            detail="Requirement analysis not found."
        )

    try:
        result = await architecture_agent.generate_architecture(
            requirement
        )

        architecture = ArchitecturePlan(
            project_id=requirement.project_id,
            requirement_analysis_id=requirement.id,
            architecture_result=result.model_dump(mode="json")
        )

        db.add(architecture)
        db.commit()
        db.refresh(architecture)

        return architecture

    except (ValueError, RuntimeError) as error:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )


@router.get(
    "/{architecture_id}",
    response_model=ArchitecturePlanResponse
)
def get_architecture(
    architecture_id: int,
    db: Session = Depends(get_db)
):
    architecture = db.query(ArchitecturePlan).filter(
        ArchitecturePlan.id == architecture_id
    ).first()

    if not architecture:
        raise HTTPException(
            status_code=404,
            detail="Architecture plan not found."
        )

    return architecture


@router.get(
    "/projects/{project_id}",
    response_model=list[ArchitecturePlanResponse]
)
def get_project_architectures(
    project_id: int,
    db: Session = Depends(get_db)
):
    return db.query(ArchitecturePlan).filter(
        ArchitecturePlan.project_id == project_id
    ).order_by(
        ArchitecturePlan.created_at.desc()
    ).all()