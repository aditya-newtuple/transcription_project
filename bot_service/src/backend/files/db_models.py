# files/db_models.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from common.logger import logger
from common.models import JobStatus
from database.manager import Base, DatabaseServiceManager
from files.models.request import CreateFileRequest

if TYPE_CHECKING:
    from jobs.db_models import Job  # type-only
    from transcripts.db_models import Transcript  # type-only

class File(Base):
    __tablename__ = "file"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source_name: Mapped[Optional[str]] = mapped_column(String)
    path: Mapped[Optional[str]] = mapped_column(String)
    mime_type: Mapped[Optional[str]] = mapped_column(String)
    bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="queued",
    )

    queued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    message: Mapped[Optional[str]] = mapped_column(Text)

    job: Mapped["Job"] = relationship("Job", back_populates="files")
    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript", 
        back_populates="file", 
        cascade="all, delete-orphan",
        lazy="joined"  # This will load transcripts automatically with the file
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, job_id={self.job_id}, status={self.status})>"


class FileModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

    def create_file(self, request: CreateFileRequest, created_by: int) -> File:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            file = File(
                job_id=request.job_id,
                created_by=created_by,
                status=JobStatus.QUEUED,
            )
            db.add(file)
            db.commit()
            db.refresh(file)
            return file

    def update_file_paths(self, file_id: int, path: str, source_name: str, mime_type: str, bytes: int) -> Optional[File]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                return None

            file.path = path
            file.source_name = source_name
            file.mime_type = mime_type
            file.bytes = bytes

            db.commit()
            db.refresh(file)
            return file

    def get_file(self, file_id: int) -> Optional[File]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            return db.query(File).filter(File.id == file_id).first()

    def list_files(self, job_id: Optional[int] = None, status: Optional[JobStatus] = None, page_size: int = 10) -> List[File]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            query = db.query(File)
            if job_id is not None:
                query = query.filter(File.job_id == job_id)
            if status is not None:
                query = query.filter(File.status == status)
            
            # Return latest files first with pagination
            return query.order_by(File.queued_at.desc()).limit(page_size).all()

    def update_file_status(self, file_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[File]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                return None

            file.status = status
            if message is not None:
                file.message = message

            if status == JobStatus.RUNNING and not file.started_at:
                file.started_at = datetime.utcnow()
            elif status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED):
                file.finished_at = datetime.utcnow()

            db.commit()
            db.refresh(file)
            return file

    def delete_file(self, file_id: int) -> bool:
        """Delete a file and its associated transcripts.
        
        Args:
            file_id: The ID of the file to delete
            
        Returns:
            bool: True if file was found and deleted, False if file was not found
        """
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                return False
                
            db.delete(file)  # This will cascade delete associated transcripts
            db.commit()
            return True