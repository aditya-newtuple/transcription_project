from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from common.models import BatchStatus
from files.models.response import FileResponse


class JobResponse(BaseModel):
    id: int
    created_by: int
    status: BatchStatus
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    finished_at: Optional[datetime]
    message: Optional[str]

    class Config:
        from_attributes = True


class JobWithFilesResponse(JobResponse):
    id: int
    created_by: int
    status: BatchStatus
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    finished_at: Optional[datetime]
    message: Optional[str]
    files: List[FileResponse]
