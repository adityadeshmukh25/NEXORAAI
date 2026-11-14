from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=5000)
    tech_stack: str = Field(default="Python FastAPI, React, SQLite", max_length=300)

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    tech_stack: str
    status: str
    created_at: datetime
    updated_at: datetime

class HealthResponse(BaseModel):
    status: str
    database: str
    app: str
