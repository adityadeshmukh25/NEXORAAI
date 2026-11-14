from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# Generated source file

class GeneratedFile(BaseModel):
    path: str
    content: str
    language: str
    description: Optional[str] = None


# Code generation request

class CodeGenerationRequest(BaseModel):
    architecture_plan_id: int

    instructions: Optional[str] = Field(
        default=None,
        description="Additional instructions for code generation"
    )


# Code generation result

class CodeGenerationResult(BaseModel):
    summary: str

    generated_files: list[GeneratedFile] = Field(
        default_factory=list
    )


# API response

class CodeGenerationResponse(BaseModel):
    id: int
    project_id: int
    architecture_plan_id: int
    status: str
    summary: Optional[str] = None

    generated_files: list[GeneratedFile] = Field(
        default_factory=list
    )

    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)