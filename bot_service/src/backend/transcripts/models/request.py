from typing import Optional

from pydantic import BaseModel, Field

from common.models import TranscriptFormat


class CreateTranscriptRequest(BaseModel):
    file_id: int
    format: TranscriptFormat
    content: str
    version: Optional[int] = Field(default=1, ge=1)


class ApproveTranscriptRequest(BaseModel):
    approved_by: int
