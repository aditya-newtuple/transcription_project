from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from common.models import BatchStatus
from jobs.manager import JobManager
from jobs.models.response import JobResponse, JobWithFilesResponse, PaginatedJobResponse


class JobsRestController:
    # Define allowed file extensions for job uploads
    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(
        self, 
        job_manager: JobManager,
    ):
        self.job_manager = job_manager

    def prepare(self, app: APIRouter) -> None:
        @app.post("/jobs", tags=["jobs"], response_model=JobResponse)
        async def create_job(
            files: List[UploadFile] = File(...),
            # TODO: Get actual user ID from auth
            current_user_id: int = 1
        ):
            """
            Create a new job with files. A maximum of 5 files can be uploaded at a time with each file size less than 100MB.
            """
            # Validate file extensions
            for file in files:
                if not file.filename:
                    raise HTTPException(status_code=400, detail="File must have a filename")
                
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File '{file.filename}' has an unsupported format. "
                               f"Allowed formats are: {', '.join(self.ALLOWED_EXTENSIONS)}"
                    )
            
            return await self.job_manager.create_job_with_files(
                files=files,
                created_by=current_user_id
            )

        @app.get("/jobs/{job_id}", tags=["jobs"], response_model=JobWithFilesResponse)
        def get_job(job_id: int):
            """
            Get a job by its ID.
            """
            job = self.job_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return job

        @app.get("/jobs", tags=["jobs"], response_model=PaginatedJobResponse)
        def list_jobs(
            created_by: Optional[int] = Query(default=None, description="Filter by user ID"),
            status: Optional[BatchStatus] = Query(default=None, description="Filter by job status"),
            file_name: Optional[str] = Query(default=None, description="Search by file name (partial match)"),
            tags: Optional[List[str]] = Query(default=None, description="Filter by tags (supports multiple)"),
            date_from: Optional[datetime] = Query(default=None, description="Filter by upload date range (start date)"),
            date_to: Optional[datetime] = Query(default=None, description="Filter by upload date range (end date)"),
            sort_by: Optional[str] = Query(default=None, description="Sort by 'file_name' or 'status'"),
            sort_direction: Optional[str] = Query(default="desc", description="Sort direction: 'asc' or 'desc'"),
            page_size: int = Query(default=10, ge=1, le=50, description="Number of jobs to return"),
            page_number: int = Query(default=1, ge=1, description="Page number to return"),
        ):
            """
            List jobs with search, filtering, sorting, and pagination.
            """
            return self.job_manager.list_jobs(
                created_by=created_by,
                status=status,
                file_name=file_name,
                tags=tags,
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_size=page_size,
                page_number=page_number
            )

        @app.put("/jobs/{job_id}/status", tags=["jobs"], response_model=JobResponse)
        def update_job_status(
            job_id: int,
            status: BatchStatus,
        ):
            """
            Update a job's status.
            """
            job = self.job_manager.update_job_status(job_id, status)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return job
