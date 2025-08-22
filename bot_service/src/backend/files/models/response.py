from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from common.models import JobStatus
from transcripts.models.response import TranscriptResponse


class FileResponse(BaseModel):
    id: int
    job_id: int
    created_by: int
    source_name: Optional[str]
    path: Optional[str]
    mime_type: Optional[str]
    bytes: Optional[int]
    deleted_at: Optional[datetime]
    status: JobStatus
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    message: Optional[str]

    class Config:
        from_attributes = True


class FileStatusResponse(BaseModel):
    status: JobStatus
    message: Optional[str]
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class FileWithTranscriptsResponse(FileResponse):
    transcripts: List[TranscriptResponse] = []
