from typing import List, Optional

from common.models import JobStatus
from jobs.db_models import JobModelService
from jobs.models.request import CreateJobRequest
from jobs.models.response import JobResponse, JobWithFilesResponse


class JobManager:
    def __init__(self, job_model_service: JobModelService) -> None:
        self.job_model_service = job_model_service

    def create_job(self, request: CreateJobRequest, created_by: int) -> JobResponse:
        job = self.job_model_service.create_job(request, created_by)
        return JobResponse.from_orm(job)

    def get_job(self, job_id: int) -> Optional[JobWithFilesResponse]:
        job = self.job_model_service.get_job(job_id)
        if not job:
            return None
        return JobWithFilesResponse.from_orm(job)

    def list_jobs(self, created_by: Optional[int] = None, status: Optional[JobStatus] = None) -> List[JobResponse]:
        jobs = self.job_model_service.list_jobs(created_by, status)
        return [JobResponse.from_orm(job) for job in jobs]

    def update_job_status(self, job_id: int, status: JobStatus) -> Optional[JobResponse]:
        job = self.job_model_service.update_job_status(job_id, status)
        if not job:
            return None
        return JobResponse.from_orm(job)

    def update_job_counts(self, job_id: int) -> Optional[JobResponse]:
        job = self.job_model_service.update_job_counts(job_id)
        if not job:
            return None
        return JobResponse.from_orm(job)
