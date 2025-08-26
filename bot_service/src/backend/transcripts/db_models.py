# transcripts/db_models.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, and_, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from common.logger import logger
from common.models import TranscriptFormat
from database.manager import Base, DatabaseServiceManager
from exceptions.db import DBException
from transcripts.models.request import CreateTranscriptRequest


# class Transcript(Base):
#     __tablename__ = "transcripts"

#     id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
#     file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("file.id", ondelete="CASCADE"), nullable=False)
#     version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    
#     format: Mapped[TranscriptFormat] = mapped_column(
#         Enum(TranscriptFormat, name="transcript_format", values_callable=lambda e: [m.value for m in e]),
#         nullable=False,
#         server_default="txt",
#     )
    
#     content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
#     created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
#     approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
#     approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
#     is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

#     # Forward ref; no runtime import
#     file: Mapped["File"] = relationship(
#         "File", 
#         back_populates="transcripts",
#         lazy="joined"  # This will load the file automatically with the transcript
#     )

#     def __repr__(self) -> str:
#         return f"<Transcript(id={self.id}, file_id={self.file_id}, version={self.version}, format={self.format})>"

class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # split content
    srt_content: Mapped[Optional[str]] = mapped_column(Text)
    text_content: Mapped[Optional[str]] = mapped_column(Text)

    # approval metadata
    approved_by: Mapped[Optional[str]] = mapped_column(String)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # misc
    message: Mapped[Optional[str]] = mapped_column(Text)
    language_hint: Mapped[Optional[str]] = mapped_column(String)
    transcription_process_duration: Mapped[Optional[int]] = mapped_column(Integer)
    transcription_model: Mapped[Optional[str]] = mapped_column(String)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)  
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("now()"))

    file = relationship("File", back_populates="transcripts", lazy="joined")

    def __repr__(self) -> str:
        return f"<Transcript id={self.id} file_id={self.file_id} v={self.version} active={self.active}>"


class TranscriptModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

    def create_transcript(self, request: CreateTranscriptRequest, created_by: int) -> Transcript:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                # Set default message if not provided
                message = request.message if hasattr(request, 'message') and request.message else "Transcript created successfully with both text and SRT formats"
                
                transcript = Transcript(
                    file_id=request.file_id,
                    version=request.version,
                    srt_content=request.srt_content,
                    text_content=request.text_content,
                    language_hint=request.language_hint or "en",
                    transcription_process_duration=request.transcription_process_duration or 0,
                    transcription_model=request.transcription_model,
                    created_by=created_by,
                    message=message
                )
                db.add(transcript)
                db.commit()
                db.refresh(transcript)
                return transcript
        except DBException as e:
            raise DBException(f"Could not create transcript due to {e}")

    def update_transcript_metadata(self, transcript_id: int, duration: int = None, model: str = None, language: str = None, message: str = None) -> Optional[Transcript]:
        """Update transcript metadata after transcription completion."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
                if not transcript:
                    return None

                if duration is not None:
                    transcript.transcription_process_duration = duration
                if model is not None:
                    transcript.transcription_model = model
                if language is not None:
                    transcript.language_hint = language
                if message is not None:
                    transcript.message = message

                db.commit()
                db.refresh(transcript)
                return transcript
        except DBException as e:
            raise DBException(f"Could not update transcript metadata due to {e}")

    def get_transcript(self, transcript_id: int) -> Optional[Transcript]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                return db.query(Transcript).filter(Transcript.id == transcript_id).first()
        except DBException as e:
            raise DBException(f"Could not get transcript due to {e}")

    def list_transcripts(self, file_id: Optional[int] = None, active: Optional[bool] = None, page_size: int = 10) -> List[Transcript]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(Transcript)
                if file_id is not None:
                    query = query.filter(Transcript.file_id == file_id)
                if active is not None:
                    query = query.filter(Transcript.active == active)
                
                # Return latest transcripts first with pagination
                return query.order_by(Transcript.created_at.desc()).limit(page_size).all()
        except DBException as e:
            raise DBException(f"Could not list transcripts due to {e}")

    def approve_transcript(self, transcript_id: int, approved_by: str) -> Optional[Transcript]:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
                if not transcript:
                    return None

                # First, deactivate any other transcripts for this file
                db.query(Transcript).filter(
                    and_(
                        Transcript.file_id == transcript.file_id,
                        Transcript.id != transcript_id
                    )
                ).update({"active": False})

                # Then activate this one
                transcript.active = True
                transcript.approved_by = approved_by
                transcript.approved_at = datetime.utcnow()
                transcript.message = f"Transcript approved by {approved_by} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}. This transcript is now the active version for the file."

                db.commit()
                db.refresh(transcript)
                return transcript
        except DBException as e:
            raise DBException(f"Could not approve transcript due to {e}")
