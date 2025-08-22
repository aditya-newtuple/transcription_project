from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from common.models import TranscriptFormat


class TranscriptResponse(BaseModel):
    id: int
    file_id: int
    version: int
    format: TranscriptFormat
    content: Optional[str]
    created_at: datetime
    created_by: Optional[int]
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    is_approved: bool

    class Config:
        from_attributes = True
