from typing import Optional

from pydantic import BaseModel, Field


class CreateTranscriptRequest(BaseModel):
    file_id: int
    version: Optional[int] = Field(default=1, ge=1)
    srt_content: Optional[str] = None
    text_content: Optional[str] = None
    language_hint: Optional[str] = None
    transcription_process_duration: Optional[int] = None
    transcription_model: Optional[str] = None
    message: Optional[str] = None

class ApproveTranscriptRequest(BaseModel):
    approved_by: str
