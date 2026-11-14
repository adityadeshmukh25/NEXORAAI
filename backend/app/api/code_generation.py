from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.architecture_plan import ArchitecturePlan
from app.models.code_generation import CodeGeneration
from app.services.file_writer import file_writer
from app.services.project_validator import project_validator
from app.services.code_validator import code_validator
from app.schemas.code_generation import (
    CodeGenerationRequest,
    CodeGenerationResponse
)

from app.services.code_generation_agent import (
    code_generation_agent
)


router = APIRouter(
    prefix="/code-generation",
    tags=["Code Generation"]
)


# Generate project source code

@router.post(
    "/generate",
    response_model=CodeGenerationResponse
)
async def generate_project_code(
    request: CodeGenerationRequest,
    db: Session = Depends(get_db)
):

    architecture = db.query(ArchitecturePlan).filter(
        ArchitecturePlan.id == request.architecture_plan_id
    ).first()

    if not architecture:
        raise HTTPException(
            status_code=404,
            detail="Architecture plan not found."
        )

    try:

        result = await code_generation_agent.generate_code(
            architecture=architecture,
            instructions=request.instructions
        )

        generation = CodeGeneration(
            project_id=architecture.project_id,
            architecture_plan_id=architecture.id,
            status="completed",
            summary=result.summary,
            generated_files=[
                file.model_dump()
                for file in result.generated_files
            ]
        )

        db.add(generation)
        db.commit()
        db.refresh(generation)

        return generation

    except (ValueError, RuntimeError) as error:

        db.rollback()

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )


# Retrieve a particular code generation

@router.get(
    "/{generation_id}",
    response_model=CodeGenerationResponse
)
def get_code_generation(
    generation_id: int,
    db: Session = Depends(get_db)
):

    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found."
        )

    return generation


# Retrieve all code generations for a project

@router.get(
    "/projects/{project_id}",
    response_model=list[CodeGenerationResponse]
)
def get_project_code_generations(
    project_id: int,
    db: Session = Depends(get_db)
):

    return db.query(CodeGeneration).filter(
        CodeGeneration.project_id == project_id
    ).order_by(
        CodeGeneration.created_at.desc()
    ).all()

# Write generated source code into the project workspace

@router.post("/{generation_id}/write")
def write_generated_code(
    generation_id: int,
    db: Session = Depends(get_db)
):

    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found."
        )

    try:

        result = file_writer.write_generation(generation)

        return {
            "message": "Generated files saved successfully.",
            "generation_id": generation.id,
            "status": "saved",
            "workspace": result["workspace"],
            "file_count": result["file_count"],
            "files": result["files"]
        }

    except (ValueError, OSError) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

@router.post("/{generation_id}/validate")
def validate_generated_code(
    generation_id: int,
    db: Session = Depends(get_db)
):
    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found."
        )

    result = code_validator.validate_generation(generation)

    return result

@router.post("/{generation_id}/validate-structure")
def validate_project_structure(
    generation_id: int,
    db: Session = Depends(get_db)
):
    generation = db.query(CodeGeneration).filter(
        CodeGeneration.id == generation_id
    ).first()

    if not generation:
        raise HTTPException(
            status_code=404,
            detail="Code generation record not found."
        )

    result = project_validator.validate_generation(generation)

    return result