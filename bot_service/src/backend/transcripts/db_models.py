# transcripts/db_models.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, and_, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from common.logger import logger
from common.models import TranscriptFormat
from database.manager import Base, DatabaseServiceManager
from transcripts.models.request import CreateTranscriptRequest

if TYPE_CHECKING:
    from files.db_models import File  # type-only

class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    
    format: Mapped[TranscriptFormat] = mapped_column(
        Enum(TranscriptFormat, name="transcript_format", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="txt",
    )
    
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Forward ref; no runtime import
    file: Mapped["File"] = relationship(
        "File", 
        back_populates="transcripts",
        lazy="joined"  # This will load the file automatically with the transcript
    )

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, file_id={self.file_id}, version={self.version}, format={self.format})>"

class TranscriptModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

        # ⚠️ Recommended: let Alembic manage schema; comment out in prod
        # try:
        #     if Base:
        #         logger.info("Creating base tables for transcripts..")
        #         Base.metadata.create_all(bind=self.current_db_engine)
        # except Exception as e:
        #     logger.error(f"Could not create base tables for transcripts due to {e}")

    def create_transcript(self, request: CreateTranscriptRequest, created_by: int) -> Transcript:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            transcript = Transcript(
                file_id=request.file_id,
                version=request.version,
                format=request.format,
                content=request.content,
                created_by=created_by
            )
            db.add(transcript)
            db.commit()
            db.refresh(transcript)
            return transcript

    def get_transcript(self, transcript_id: int) -> Optional[Transcript]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            return db.query(Transcript).filter(Transcript.id == transcript_id).first()

    def list_transcripts(self, file_id: Optional[int] = None, is_approved: Optional[bool] = None, page_size: int = 10) -> List[Transcript]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            query = db.query(Transcript)
            if file_id is not None:
                query = query.filter(Transcript.file_id == file_id)
            if is_approved is not None:
                query = query.filter(Transcript.is_approved == is_approved)
            
            # Return latest transcripts first with pagination
            return query.order_by(Transcript.created_at.desc()).limit(page_size).all()

    def approve_transcript(self, transcript_id: int, approved_by: int) -> Optional[Transcript]:
        with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
            transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
            if not transcript:
                return None

            # First, un-approve any other transcripts for this file/format
            db.query(Transcript).filter(
                and_(
                    Transcript.file_id == transcript.file_id,
                    Transcript.format == transcript.format,
                    Transcript.id != transcript_id
                )
            ).update({"is_approved": False})

            # Then approve this one
            transcript.is_approved = True
            transcript.approved_by = approved_by
            transcript.approved_at = datetime.utcnow()

            db.commit()
            db.refresh(transcript)
            return transcript
