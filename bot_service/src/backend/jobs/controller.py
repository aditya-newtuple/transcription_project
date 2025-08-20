from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from common.models import JobStatus
from jobs.manager import JobManager
from jobs.models.request import CreateJobRequest
from jobs.models.response import JobResponse, JobWithFilesResponse


class JobsRestController:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    def prepare(self, app: APIRouter) -> None:
        @app.post("/jobs", tags=["jobs"], response_model=JobResponse)
        def create_job(
            request: CreateJobRequest,
            # TODO: Get actual user ID from auth
            current_user_id: int = 1
        ):
            return self.job_manager.create_job(request, current_user_id)

        @app.get("/jobs/{job_id}", tags=["jobs"], response_model=JobWithFilesResponse)
        def get_job(job_id: int):
            job = self.job_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return job

        @app.get("/jobs", tags=["jobs"], response_model=List[JobResponse])
        def list_jobs(
            created_by: Optional[int] = None,
            status: Optional[JobStatus] = None,
        ):
            return self.job_manager.list_jobs(created_by, status)

        @app.put("/jobs/{job_id}/status", tags=["jobs"], response_model=JobResponse)
        def update_job_status(
            job_id: int,
            status: JobStatus,
        ):
            job = self.job_manager.update_job_status(job_id, status)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            return job
