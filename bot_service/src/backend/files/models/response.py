from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from common.models import FileStatus
from transcripts.models.response import TranscriptResponse


class FileResponse(BaseModel):
    id: int
    job_id: int
    created_by: int
    sequence_no: Optional[int]
    source_name: Optional[str]
    source_path: Optional[str]
    source_mime: Optional[str]
    source_bytes: Optional[int]
    source_uploaded_at: datetime
    source_deleted_at: Optional[datetime]
    status: FileStatus
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    language_hint: Optional[str]
    duration_sec: Optional[int]

    class Config:
        from_attributes = True

class FileStatusResponse(BaseModel):
    status: FileStatus
    error_message: Optional[str]
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

class FileWithTranscriptsResponse(FileResponse):
    transcripts: List[TranscriptResponse] = []
