# files/db_models.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from common.logger import logger
from common.models import JobStatus
from database.manager import Base, DatabaseServiceManager
from exceptions.db import DBException
from files.models.request import CreateFileRequest


# class File(Base):
#     __tablename__ = "file"

#     id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
#     job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
#     created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

#     source_name: Mapped[Optional[str]] = mapped_column(String)
#     path: Mapped[Optional[str]] = mapped_column(String)
#     mime_type: Mapped[Optional[str]] = mapped_column(String)
#     bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
#     deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

#     status: Mapped[JobStatus] = mapped_column(
#         Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
#         nullable=False,
#         server_default="queued",
#     )

#     queued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
#     started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
#     finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
#     message: Mapped[Optional[str]] = mapped_column(Text)

#     job: Mapped["Job"] = relationship("Job", back_populates="files")
#     transcripts: Mapped[List["Transcript"]] = relationship(
#         "Transcript", 
#         back_populates="file", 
#         cascade="all, delete-orphan",
#         lazy="joined"  # This will load transcripts automatically with the file
#     )

#     def __repr__(self) -> str:
#         return f"<File(id={self.id}, job_id={self.job_id}, status={self.status})>"
class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    file_name: Mapped[Optional[str]] = mapped_column(String)
    path: Mapped[Optional[str]] = mapped_column(String)
    mimetype: Mapped[Optional[str]] = mapped_column(String)
    bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="queued",
    )

    queued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(UTC))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    message: Mapped[Optional[str]] = mapped_column(Text)

    tags: Mapped[Optional[str]] = mapped_column(String)

    job = relationship("Job", back_populates="files")
    transcripts = relationship(
        "Transcript", back_populates="file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} job_id={self.job_id} status={self.status}>"


class FileModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine


    def create_file(self, request: CreateFileRequest, created_by: int) -> File:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                file = File(
                    job_id=request.job_id,
                    created_by=created_by,
                    status=JobStatus.QUEUED,
                    message="File created and queued for transcription processing"
                )
                db.add(file)
                db.commit()
                db.refresh(file)
                return file
        except DBException as e:
            raise DBException(f"Could not create file due to {e}")

    def update_file_paths(self, file_id: int, path: str, file_name: str, mimetype: str, bytes: int, 
                         language_hint: Optional[str] = None, duration_sec: Optional[int] = None, 
                         tags: Optional[str] = None) -> Optional[File]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return None

                file.path = path
                file.file_name = file_name
                file.mimetype = mimetype
                file.bytes = bytes
                
                if language_hint is not None:
                    file.language_hint = language_hint
                if duration_sec is not None:
                    file.durationSec = duration_sec
                if tags is not None:
                    file.tags = tags

                db.commit()
                db.refresh(file)
                return file
        except DBException as e:
            raise DBException(f"Could not update file paths due to {e}")

    def update_transcription_metadata(self, file_id: int, tags: Optional[str] = None) -> Optional[File]:
        """Update only transcription-related metadata without changing file paths or basic info."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return None

                if tags is not None:
                    file.tags = tags

                db.commit()
                db.refresh(file)
                return file
        except DBException as e:
            raise DBException(f"Could not update transcription metadata due to {e}")

    def get_file(self, file_id: int) -> Optional[File]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                return db.query(File).options(selectinload(File.transcripts)).filter(File.id == file_id).first()
        except DBException as e:
            raise DBException(f"Could not get file due to {e}")

    # def list_files(self, job_id: Optional[int] = None, status: Optional[JobStatus] = None, page_size: int = 10) -> List[File]:
    #     try:
    #         with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
    #             query = db.query(File)
    #             if job_id is not None:
    #                 query = query.filter(File.job_id == job_id)
    #             if status is not None:
    #                 query = query.filter(File.status == status)
                
    #             # Return latest files first with pagination
    #             return query.order_by(File.queued_at.desc()).limit(page_size).all()
    #     except DBException as e:
    #         raise DBException(f"Could not list files due to {e}")

    def list_files(
        self,
        job_id: Optional[int] = None,
        status: Optional[JobStatus] = None,
        file_name: Optional[str] = None,
        tags: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_direction: Optional[str] = None,
        page_size: int = 10,
        page_number: int = 1
    ) -> List[File]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(File)
                
                if job_id is not None:
                    query = query.filter(File.job_id == job_id)
                if status is not None:
                    query = query.filter(File.status == status)
                if file_name is not None:
                    query = query.filter(File.file_name.like(f"%{file_name}%"))
                if tags is not None:
                    query = query.filter(File.tags.like(f"%{tags}%"))
                if date_from is not None:
                    query = query.filter(File.created_at >= date_from)
                if date_to is not None:
                    query = query.filter(File.created_at <= date_to)
                if sort_by is not None:
                    if sort_by == "file_name":
                        query = query.order_by(File.file_name.asc() if sort_direction == "asc" else File.file_name.desc())
                    elif sort_by == "status":
                        query = query.order_by(File.status.asc() if sort_direction == "asc" else File.status.desc())
                    elif sort_by == "created_at":
                        query = query.order_by(File.created_at.asc() if sort_direction == "asc" else File.created_at.desc())
                    elif sort_by == "queued_at":
                        query = query.order_by(File.queued_at.asc() if sort_direction == "asc" else File.queued_at.desc())
                    elif sort_by == "started_at":
                        query = query.order_by(File.started_at.asc() if sort_direction == "asc" else File.started_at.desc())
                    elif sort_by == "finished_at":
                        query = query.order_by(File.finished_at.asc() if sort_direction == "asc" else File.finished_at.desc())
                else:
                    query = query.order_by(File.created_at.desc())

                return query.offset((page_number - 1) * page_size).limit(page_size).all()
        except DBException as e:
            raise DBException(f"Could not list files due to {e}")

    def update_file_status(self, file_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[File]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return None

                file.status = status
                
                # Set meaningful default messages if none provided
                if message is None:
                    if status == JobStatus.QUEUED:
                        message = "File queued for transcription processing"
                    elif status == JobStatus.RUNNING:
                        message = "File is currently being transcribed"
                    elif status == JobStatus.SUCCEEDED:
                        message = "File transcription completed successfully"
                    elif status == JobStatus.FAILED:
                        message = "File transcription failed"
                    elif status == JobStatus.CANCELED:
                        message = "File transcription was canceled"
                
                file.message = message

                if status == JobStatus.RUNNING and not file.started_at:
                    file.started_at = datetime.now(UTC)
                elif status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED):
                    file.finished_at = datetime.now(UTC)

                db.commit()
                db.refresh(file)
                return file
        except DBException as e:
            raise DBException(f"Could not update file status due to {e}")

    def delete_file(self, file_id: int) -> bool:
        """Delete a file and its associated transcripts.
        
        Args:
            file_id: The ID of the file to delete
            
        Returns:
            bool: True if file was found and deleted, False if file was not found
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return False
                    
                db.delete(file)  # This will cascade delete associated transcripts
                db.commit()
                return True
        except DBException as e:
            raise DBException(f"Could not delete file due to {e}")