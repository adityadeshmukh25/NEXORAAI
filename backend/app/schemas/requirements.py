
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FunctionalRequirement(BaseModel):
    id: str
    title: str
    description: str
    priority: Literal["High", "Medium", "Low"]


class NonFunctionalRequirement(BaseModel):
    category: str
    description: str


class SuggestedModule(BaseModel):
    name: str
    description: str


class RequirementAnalysisResult(BaseModel):
    project_summary: str

    functional_requirements: list[FunctionalRequirement] = Field(
        default_factory=list
    )

    non_functional_requirements: list[NonFunctionalRequirement] = Field(
        default_factory=list
    )

    suggested_modules: list[SuggestedModule] = Field(
        default_factory=list
    )

    assumptions: list[str] = Field(default_factory=list)

    clarification_questions: list[str] = Field(
        default_factory=list
    )

    acceptance_criteria: list[str] = Field(
        default_factory=list
    )

    suggested_technology_stack: list[str] = Field(
        default_factory=list
    )

    out_of_scope: list[str] = Field(default_factory=list)


class RequirementAnalysisRequest(BaseModel):
    project_id: int
    requirements: str = Field(min_length=10, max_length=12000)


class RequirementAnalysisResponse(BaseModel):
    id: int
    project_id: int
    original_requirements: str
    analysis_result: RequirementAnalysisResult
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
