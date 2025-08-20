from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from common.models import JobStatus
from files.models.response import FileResponse


class JobResponse(BaseModel):
    id: int
    created_by: int
    status: JobStatus
    title: Optional[str]
    notes: Optional[str]
    total_count: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_summary: Optional[str]

    class Config:
        from_attributes = True


class JobWithFilesResponse(JobResponse):
    files: List[FileResponse] = []
