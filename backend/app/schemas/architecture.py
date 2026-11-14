from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# 1. System Architecture

class ArchitectureComponent(BaseModel):
    name: str
    description: str
    technology: str
    responsibilities: list[str] = Field(default_factory=list)


class SystemArchitecture(BaseModel):
    architecture_style: str
    description: str
    components: list[ArchitectureComponent] = Field(
        default_factory=list
    )
    communication_flow: list[str] = Field(
        default_factory=list
    )


# 2. Database Design

class DatabaseField(BaseModel):
    name: str
    data_type: str
    constraints: list[str] = Field(default_factory=list)


class DatabaseTable(BaseModel):
    table_name: str
    description: str
    fields: list[DatabaseField] = Field(default_factory=list)


class DatabaseRelationship(BaseModel):
    name: str
    field1: Optional[str] = None
    field2: Optional[str] = None


class DatabaseDesign(BaseModel):
    database_type: str
    tables: list[DatabaseTable] = Field(default_factory=list)
    relationships: list[DatabaseRelationship] = Field(
        default_factory=list
    )


# 3. API Design

class APIEndpoint(BaseModel):
    method: str
    endpoint: str
    description: str
    request_body: Optional[str] = None
    response: Optional[str] = None


class APIDesign(BaseModel):
    base_path: str
    endpoints: list[APIEndpoint] = Field(default_factory=list)


# 4. Project Structure

class ProjectDirectory(BaseModel):
    path: str
    description: str


class ProjectStructure(BaseModel):
    directories: list[ProjectDirectory] = Field(
        default_factory=list
    )


# 5. Development Roadmap

class DevelopmentPhase(BaseModel):
    phase: int
    title: str
    tasks: list[str] = Field(default_factory=list)
    estimated_effort: str


# 6. Technology Recommendations

class TechnologyRecommendation(BaseModel):
    category: str
    technology: str
    reason: str


# 7. Complete Architecture Plan

class ArchitecturePlanResult(BaseModel):

    project_overview: str

    system_architecture: SystemArchitecture

    database_design: DatabaseDesign

    api_design: APIDesign

    project_structure: ProjectStructure

    technology_recommendations: list[
        TechnologyRecommendation
    ] = Field(default_factory=list)

    development_roadmap: list[
        DevelopmentPhase
    ] = Field(default_factory=list)

    security_recommendations: list[str] = Field(
        default_factory=list
    )

    scalability_recommendations: list[str] = Field(
        default_factory=list
    )


# 8. API Request

class ArchitecturePlanRequest(BaseModel):
    requirement_analysis_id: int


# 9. API Response

class ArchitecturePlanResponse(BaseModel):
    id: int
    project_id: int
    requirement_analysis_id: int
    architecture_result: ArchitecturePlanResult
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)