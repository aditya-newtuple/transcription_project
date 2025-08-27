from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from common.models import JobStatus
from transcripts.models.response import TranscriptResponse

class FileResponse(BaseModel):
    id: int
    job_id: int
    created_by: int
    file_name: Optional[str]
    path: Optional[str]
    mimetype: Optional[str]
    bytes: Optional[int]
    created_at: datetime
    deleted_at: Optional[datetime]
    status: JobStatus
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    message: Optional[str]
    tags: Optional[str]

    class Config:
        from_attributes = True
        orm_mode = True


class FileStatusResponse(BaseModel):
    status: JobStatus
    message: Optional[str]
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

class FileWithTranscriptsResponse(BaseModel):
    id: int
    job_id: int
    created_by: int
    file_name: Optional[str]
    path: Optional[str]
    mimetype: Optional[str]
    bytes: Optional[int]
    created_at: datetime
    deleted_at: Optional[datetime]
    status: JobStatus
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    message: Optional[str]
    tags: Optional[str]
    transcripts: List[TranscriptResponse]

    class Config:
        from_attributes = True
        orm_mode = True
