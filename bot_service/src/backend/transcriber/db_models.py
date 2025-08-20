import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import UUID

from database.manager import Base, DatabaseServiceManager
from common.logger import get_logger

logger = get_logger(__name__)

class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String, nullable=False, default="pending")
    original_filename = Column(String, nullable=True)
    processed_file_path = Column(String, nullable=True)
    output_file_path = Column(String, nullable=True)  # Keep for backward compatibility
    output_files = Column(JSON, nullable=True)  # New column to store multiple output paths
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(BigInteger, primary_key=True)
    created_by = Column(BigInteger, nullable=False)
    status = Column(Enum('created', 'queued', 'running', 'completed', 'failed', 'canceled', name='batch_status'), nullable=False, server_default='created')
    title = Column(String)
    notes = Column(Text)
    
    total_count = Column(Integer, nullable=False, server_default='0')
    queued_count = Column(Integer, nullable=False, server_default='0')
    running_count = Column(Integer, nullable=False, server_default='0')
    succeeded_count = Column(Integer, nullable=False, server_default='0')
    failed_count = Column(Integer, nullable=False, server_default='0')
    skipped_count = Column(Integer, nullable=False, server_default='0')
    
    created_at = Column(DateTime, nullable=False, server_default=text('now()'))
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error_summary = Column(Text)

    # Relationships
    files = relationship("File", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status}, title={self.title})>"

class File(Base):
    __tablename__ = 'file'

    id = Column(BigInteger, primary_key=True)
    job_id = Column(BigInteger, ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(BigInteger, nullable=False)
    sequence_no = Column(Integer)
    source_name = Column(String)
    source_path = Column(String)
    source_mime = Column(String)
    source_bytes = Column(BigInteger)
    source_uploaded_at = Column(DateTime, nullable=False, server_default=text('now()'))
    source_deleted_at = Column(DateTime)
    status = Column(Enum('queued', 'running', 'succeeded', 'failed', 'canceled', name='job_status'), nullable=False, server_default='queued')
    queued_at = Column(DateTime, nullable=False, server_default=text('now()'))
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error_message = Column(Text)
    language_hint = Column(String)
    duration_sec = Column(Integer)

    # Relationships
    job = relationship("Job", back_populates="files")
    transcripts = relationship("Transcript", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<File(id={self.id}, job_id={self.job_id}, status={self.status})>"

class Transcript(Base):
    __tablename__ = 'transcripts'

    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger, ForeignKey('file.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, nullable=False, server_default='1')
    format = Column(Enum('txt', 'srt', name='transcript_format'), nullable=False, server_default='txt')
    content = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=text('now()'))
    created_by = Column(BigInteger)
    approved_at = Column(DateTime)
    approved_by = Column(BigInteger)
    is_approved = Column(Boolean, nullable=False, server_default='false')

    # Relationships
    file = relationship("File", back_populates="transcripts")

    def __repr__(self):
        return f"<Transcript(id={self.id}, file_id={self.file_id}, version={self.version}, format={self.format})>"

class TranscriptionJobModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

        try:
            if Base:
                logger.info("Creating base tables for transcription jobs..")
                Base.metadata.create_all(bind=self.current_db_engine)
        except Exception as e:
            logger.error(f"Could not create base tables for transcription jobs due to {e}")
