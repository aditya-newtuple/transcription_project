from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TranscriptResponse(BaseModel):
    id: int
    file_id: int
    version: int
    srt_content: Optional[str]
    text_content: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    active: bool
    message: Optional[str]
    language_hint: Optional[str]
    transcription_process_duration: Optional[int]
    transcription_model: Optional[str]
    created_at: datetime
    created_by: Optional[int]

    class Config:
        from_attributes = True
