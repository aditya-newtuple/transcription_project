import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from database.manager import DatabaseServiceManager
from common.logger import logger

Base = declarative_base()

class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False, default="queued")
    original_filename = Column(String, nullable=False)
    processed_file_path = Column(String, nullable=True)
    output_file_path = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

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
