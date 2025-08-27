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
        orm_mode = True

class FilterParams(BaseModel):
    search_query: Optional[str] = None # search query
    status: Optional[BatchStatus] = None
    tags: Optional[List[str]] = None
    created_by: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True


class PaginatedJobResponse(BaseModel):
    data: List[JobResponse]
    page: int
    page_size: int
    total_count: int
    sort_by: Optional[str] = None
    order: Optional[str] = "desc"
    filters: FilterParams

    class Config:
        from_attributes = True
        orm_mode = True


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

    class Config:
        from_attributes = True
        orm_mode = True