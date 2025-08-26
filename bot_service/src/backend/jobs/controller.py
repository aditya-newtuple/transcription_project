from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from common.models import BatchStatus
from jobs.manager import JobManager
from jobs.models.response import JobResponse, JobWithFilesResponse


class JobsRestController:
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

        @app.get("/jobs", tags=["jobs"], response_model=List[JobResponse])
        def list_jobs(
            created_by: Optional[int] = None,
            status: Optional[BatchStatus] = None,
            page_size: int = Query(default=10, ge=1, le=50, description="Number of jobs to return"),
        ):
            """
            List jobs with pagination. Returns the most recent jobs first.
            
            Parameters:
            - created_by: Filter by user ID who created the jobs
            - status: Filter by job status
            - page_size: Number of jobs to return (max 50)
            """
            return self.job_manager.list_jobs(created_by, status, page_size)

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
