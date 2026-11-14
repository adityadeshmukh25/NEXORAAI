from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CodeExecutionRequest(BaseModel):
    operation: Literal["compile_python"] = "compile_python"
    timeout_seconds: int = Field(default=30, ge=5, le=60)


class CodeExecutionResponse(BaseModel):
    id: int
    generation_id: int
    status: str

    command: Optional[str] = None
    exit_code: Optional[int] = None

    stdout: Optional[str] = None
    stderr: Optional[str] = None

    execution_time: Optional[float] = None

    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)