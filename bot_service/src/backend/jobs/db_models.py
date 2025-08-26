# jobs/db_models.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, joinedload

from common.logger import logger
from common.models import BatchStatus, JobStatus
from database.manager import Base, DatabaseServiceManager
from exceptions.db import DBException
from jobs.models.request import CreateJobRequest


# class Job(Base):
#     __tablename__ = "jobs"

#     id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
#     created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

#     status: Mapped[BatchStatus] = mapped_column(
#         Enum(BatchStatus, name="batch_status", values_callable=lambda e: [m.value for m in e]),
#         nullable=False,
#         server_default="created",
#     )

#     # progress counters (maintained by app)
#     total_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

#     created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
#     started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
#     finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
#     message: Mapped[Optional[str]] = mapped_column(Text)  # optional aggregated error

#     # Forward ref; no runtime import
#     files: Mapped[List["File"]] = relationship("File", back_populates="job", cascade="all, delete-orphan")

#     def __repr__(self) -> str:
#         return f"<Job(id={self.id}, status={self.status})>"
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="created",
    )

    title: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=datetime.now(UTC))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    message: Mapped[Optional[str]] = mapped_column(Text)

    files = relationship("File", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status}>"

class JobModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine
        logger.info(f"Connected to {self.current_db_engine.url.render_as_string(hide_password=False)}")

    def create_job(self, request: CreateJobRequest, created_by: int) -> Job:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                logger.info(f"Creating job for user {created_by}")
                
                # Generate meaningful job title and notes based on the files
                file_count = len(request.files) if hasattr(request, 'files') else 0
                
                job_title = f"Audio Transcription Job - {file_count} file(s)"

                job = Job(
                    created_by=created_by,
                    status=BatchStatus.CREATED,
                    title=job_title,
                    message="Job created successfully, files queued for transcription"
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                return job
        except DBException as e:
            raise DBException(f"Could not create job due to {e}")

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get a job by ID with its files and transcripts eagerly loaded."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                # Import here to avoid circular imports
                from files.db_models import File
                
                # Query with eager loading
                return db.query(Job).options(
                    joinedload(Job.files)
                ).filter(Job.id == job_id).first()
        except DBException as e:
            raise DBException(f"Could not get job due to {e}")

    def list_jobs(self, created_by: Optional[int] = None, status: Optional[BatchStatus] = None, page_size: int = 10) -> List[Job]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(Job)
                if created_by is not None:
                    query = query.filter(Job.created_by == created_by)
                if status is not None:
                    query = query.filter(Job.status == status)
                
                # Apply pagination and return latest jobs first
                return query.order_by(Job.created_at.desc()).limit(page_size).all()
        except DBException as e:
            raise DBException(f"Could not list jobs due to {e}")

    def update_job_status(self, job_id: int, status: BatchStatus) -> Optional[Job]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    return None

                job.status = status
                job.updated_at = datetime.utcnow()
                
                # Add meaningful status messages
                if status == BatchStatus.QUEUED:
                    job.message = "Job queued for processing, files are ready for transcription"
                elif status == BatchStatus.RUNNING:
                    job.message = "Job is currently processing audio files"
                elif status == BatchStatus.COMPLETED:
                    job.message = "Job completed successfully, all files transcribed"
                    job.finished_at = datetime.utcnow()
                elif status == BatchStatus.FAILED:
                    job.message = "Job failed during processing, check individual file statuses"
                    job.finished_at = datetime.utcnow()
                elif status == BatchStatus.CANCELED:
                    job.message = "Job was canceled by user or system"
                    job.finished_at = datetime.utcnow()

                db.commit()
                db.refresh(job)
                return job
        except DBException as e:
            raise DBException(f"Could not update job status due to {e}")

    def update_job_counts(self, job_id: int) -> Optional[Job]:
        """Update job status based on its files' statuses."""
        try:
            from files.db_models import File  # Import here to avoid circular import

            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    return None

                files = db.query(File).filter(File.job_id == job_id).all()
                
                # Update job status based on files
                if len(files) == 0:
                    job.status = BatchStatus.CREATED
                else:
                    # Check for any failed files
                    if any(f.status == JobStatus.FAILED for f in files):
                        job.status = BatchStatus.FAILED
                    # Check if all files are done (succeeded or canceled)
                    elif all(f.status in (JobStatus.SUCCEEDED, JobStatus.CANCELED) for f in files):
                        job.status = BatchStatus.COMPLETED
                    # Check if any file is running
                    elif any(f.status == JobStatus.RUNNING for f in files):
                        job.status = BatchStatus.RUNNING
                    # Check if any file is queued
                    elif any(f.status == JobStatus.QUEUED for f in files):
                        job.status = BatchStatus.QUEUED

                db.commit()
                db.refresh(job)
                return job
        except DBException as e:
            raise DBException(f"Could not update job counts due to {e}")