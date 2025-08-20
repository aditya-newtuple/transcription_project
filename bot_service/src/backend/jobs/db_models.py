# jobs/db_models.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from common.logger import logger
from common.models import FileStatus, JobStatus
from database.manager import Base, DatabaseServiceManager
from jobs.models.request import CreateJobRequest

if TYPE_CHECKING:
    from files.db_models import File  # type-only

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="batch_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="created",
    )

    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    total_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    queued_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    running_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    succeeded_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Forward ref; no runtime import
    files: Mapped[List["File"]] = relationship("File", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status={self.status}, title={self.title})>"

class JobModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

        # ⚠️ Recommended: let Alembic manage schema; comment out in prod
        # try:
        #     if Base:
        #         logger.info("Creating base tables for jobs..")
        #         Base.metadata.create_all(bind=self.current_db_engine)
        # except Exception as e:
        #     logger.error(f"Could not create base tables for jobs due to {e}")

    def create_job(self, request: CreateJobRequest, created_by: int) -> Job:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            job = Job(
                created_by=created_by,
                title=request.title,
                notes=request.notes,
                status=JobStatus.CREATED,  # works because column is Enum(JobStatus, ...)
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return job

    def get_job(self, job_id: int) -> Optional[Job]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            return db.query(Job).filter(Job.id == job_id).first()

    def list_jobs(self, created_by: Optional[int] = None, status: Optional[JobStatus] = None) -> List[Job]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            query = db.query(Job)
            if created_by is not None:
                query = query.filter(Job.created_by == created_by)
            if status is not None:
                query = query.filter(Job.status == status)
            return query.all()

    def update_job_status(self, job_id: int, status: JobStatus) -> Optional[Job]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None

            job.status = status
            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED):
                job.finished_at = datetime.utcnow()

            db.commit()
            db.refresh(job)
            return job

    def update_job_counts(self, job_id: int) -> Optional[Job]:
        # ⬇️ import here to avoid circular import at module level
        from files.db_models import File

        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None

            files = db.query(File).filter(File.job_id == job_id).all()
            job.total_count = len(files)
            job.queued_count = sum(1 for f in files if f.status == FileStatus.QUEUED)
            job.running_count = sum(1 for f in files if f.status == FileStatus.RUNNING)
            job.succeeded_count = sum(1 for f in files if f.status == FileStatus.SUCCEEDED)
            job.failed_count = sum(1 for f in files if f.status == FileStatus.FAILED)
            job.skipped_count = sum(1 for f in files if f.status == FileStatus.CANCELED)

            if job.total_count == 0:
                job.status = JobStatus.CREATED
            elif job.failed_count > 0:
                job.status = JobStatus.FAILED
            elif job.total_count == job.succeeded_count + job.skipped_count:
                job.status = JobStatus.COMPLETED
            elif job.running_count > 0:
                job.status = JobStatus.RUNNING
            elif job.queued_count > 0:
                job.status = JobStatus.QUEUED

            db.commit()
            db.refresh(job)
            return job