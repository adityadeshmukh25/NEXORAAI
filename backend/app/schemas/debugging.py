from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DebuggingRequest(BaseModel):
    generation_id: int
    execution_id: Optional[int] = None
    error_message: Optional[str] = None


class DebuggingResponse(BaseModel):
    id: int
    generation_id: int
    execution_id: Optional[int] = None

    status: str

    error_summary: Optional[str] = None
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    corrected_code: Optional[str] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)