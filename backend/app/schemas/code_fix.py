
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict


class CodeFixCreate(BaseModel):
    generation_id: int
    debugging_session_id: int
    file_path: str
    original_code: str
    corrected_code: str


class CodeFixReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    rejection_reason: Optional[str] = None


class CodeFixResponse(BaseModel):
    id: int
    generation_id: int
    debugging_session_id: int
    file_path: str
    original_code: str
    corrected_code: str
    status: str
    backup_path: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
