import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
from datetime import datetime

from faster_whisper import WhisperModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from common.logger import get_logger
from common.configuration import Configuration
from common.data_model import TranscriberConfiguration
from database.manager import DatabaseServiceManager
from transcriber.db_models import TranscriptionJob, Job, File, Transcript
from transcriber.models.interface import (
    CreateJobRequest, CreateFileRequest, CreateTranscriptRequest,
    JobResponse, FileResponse, TranscriptResponse,
    JobWithFilesResponse, FileWithTranscriptsResponse,
    JobStatus, FileStatus
)

logger = get_logger(__name__)

def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds_part:02},{milliseconds:03}"

class TranscriberManager:
    """Manages transcription jobs and Faster-Whisper model"""

    # Required files that must exist in a valid CTranslate2 model directory
    REQUIRED_MODEL_FILES = {"model.bin", "config.json", "tokenizer.json"}

    def __init__(self, config: Configuration):
        """Initialize transcription manager"""
        self.config = config.configuration()
        self.transcriber_config = self.config.transcriber_configuration
        self.db_manager = DatabaseServiceManager(config)
        self.db_session = self.db_manager.postgres_db_service().get_db_session()
        
        # Initialize model
        self._initialize_model()

    def create_job(self, file_path: str, output_formats: List[str] = ["txt", "srt"], 
                batch_id: Optional[str] = None, original_filename: Optional[str] = None,
                output_directory: Optional[str] = None) -> str:
        """Create a new transcription job in the database"""
        job_id = str(uuid4())
        
        # Use provided output directory or default to input file's parent directory
        output_dir = output_directory if output_directory else str(Path(file_path).parent)
        
        job = TranscriptionJob(
            id=job_id,
            batch_id=batch_id,
            status="pending",
            original_filename=original_filename,
            processed_file_path=file_path,
            output_file_path=output_dir
        )
        
        try:
            self.db_session.add(job)
            self.db_session.commit()
            logger.info(f"Created transcription job {job_id}")
            return job_id
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create job: {str(e)}")
            raise

    def update_job_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Update job status in database"""
        try:
            job = self.db_session.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                self.db_session.commit()
                logger.info(f"Updated job {job_id} status to {status}")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update job status: {str(e)}")
            raise

    def process_file(self, file_path: str, job_id: str, output_formats: List[str] = ["txt", "srt"]) -> None:
        """Process a transcription job"""
        try:
            # Update job status to processing
            self.update_job_status(job_id, "processing")
            
            # Get job from database
            job = self.db_session.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Ensure we have absolute paths
            input_file = Path(file_path).resolve()
            output_dir = Path(job.output_file_path).resolve()
            
            logger.info(f"Processing file: {input_file}")
            logger.info(f"Output directory: {output_dir}")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get original filename without job_id prefix and extension
            original_name = Path(job.original_filename if job.original_filename else input_file.name).stem
            if "_" in original_name:  # Remove job_id prefix if present
                original_name = original_name.split("_", 1)[1]
            
            logger.info(f"Using base filename: {original_name}")
            
            # Run transcription
            logger.info("Starting transcription...")
            segments, info = self.model.transcribe(
                str(input_file),
                beam_size=5,
                vad_filter=True
            )
            logger.info("Transcription completed")
            
            # Convert segments to list and ensure it's not empty
            segments_list = list(segments)
            if not segments_list:
                raise ValueError("No transcription segments generated")
            
            logger.info(f"Generated {len(segments_list)} segments")
            
            # Generate outputs
            output_files = {}
            
            # Generate TXT file
            if "txt" in output_formats:
                txt_path = output_dir / f"{original_name}.txt"
                logger.info(f"Creating TXT file: {txt_path}")
                with open(txt_path, "w", encoding="utf-8") as f:
                    for segment in segments_list:
                        f.write(f"{segment.text.strip()}\n")
                output_files["txt"] = str(txt_path)
                logger.info(f"TXT file created successfully")
            
            # Generate SRT file
            if "srt" in output_formats:
                srt_path = output_dir / f"{original_name}.srt"
                logger.info(f"Creating SRT file: {srt_path}")
                with open(srt_path, "w", encoding="utf-8") as f:
                    for i, segment in enumerate(segments_list, 1):
                        # Write SRT entry
                        f.write(f"{i}\n")  # Subtitle number
                        f.write(f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n")  # Timestamps
                        f.write(f"{segment.text.strip()}\n")  # Text
                        f.write("\n")  # Empty line between entries
                output_files["srt"] = str(srt_path)
                logger.info(f"SRT file created successfully")
            
            # Verify files were created
            for fmt, path in output_files.items():
                if not Path(path).exists():
                    raise FileNotFoundError(f"Failed to create {fmt.upper()} file at {path}")
                logger.info(f"Verified {fmt.upper()} file exists: {path}")
            
            # Update job with output paths
            job.output_files = output_files  # Store all output paths
            job.output_file_path = str(output_dir)  # Keep directory path for backward compatibility
            job.status = "completed"
            self.db_session.commit()
            
            logger.info(f"Successfully processed job {job_id}")
            logger.info(f"Output files: {output_files}")
            
        except Exception as e:
            logger.error(f"Failed to process job {job_id}: {str(e)}")
            self.update_job_status(job_id, "failed", str(e))
            raise

    def _initialize_model(self) -> None:
        """Initialize the Whisper model"""
        try:
            # Set up model paths
            workspace_root = Path(os.getcwd()).resolve()
            etc_directory = workspace_root / "etc"
            models_directory = Path(self.transcriber_config.models_directory or (etc_directory / "models")).resolve()
            model_instance_directory = (models_directory / self.transcriber_config.model_name).resolve()
            
            # Create directories
            etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            models_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            
            # Find or download model
            model_dir = self._find_model_directory(model_instance_directory)
            if not model_dir:
                logger.info("Downloading model...")
                self._download_model(self.transcriber_config.model_name, model_instance_directory)
                model_dir = self._find_model_directory(model_instance_directory)
                if not model_dir:
                    raise RuntimeError("Model not found after download")
            
            # Load model
            logger.info("Loading model...")
            self.model = WhisperModel(
                str(model_dir),
                device=self.transcriber_config.device,
                compute_type=self.transcriber_config.compute_type
            )
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise

    def _download_model(self, model_name: str, download_directory: Path) -> None:
        """Download model files"""
        download_directory.mkdir(parents=True, exist_ok=True)
        _ = WhisperModel(
            model_name,
            device=self.transcriber_config.device,
            compute_type=self.transcriber_config.compute_type,
            download_root=str(download_directory)
        )

    def _find_model_directory(self, preferred_directory: Path) -> Optional[Path]:
        """Find directory containing model files"""
        # Direct path
        if self._is_valid_model_directory(preferred_directory):
            return preferred_directory

        # Nested directories
        for model_file_path in preferred_directory.glob("**/model.bin"):
            if self._is_valid_model_directory(model_file_path.parent):
                return model_file_path.parent

        # HuggingFace cache structure
        root_directory = preferred_directory.parent
        model_name_hint = preferred_directory.name
        candidates = []

        # Model-specific snapshots
        for path in root_directory.glob(f"models--*{model_name_hint}*/snapshots/*/model.bin"):
            if self._is_valid_model_directory(path.parent):
                candidates.append(path.parent)

        # All snapshots as fallback
        if not candidates:
            for path in root_directory.glob("models--*/snapshots/*/model.bin"):
                if self._is_valid_model_directory(path.parent):
                    candidates.append(path.parent)

        if candidates:
            return sorted(candidates, key=lambda d: d.stat().st_mtime, reverse=True)[0]

        return None

    def _is_valid_model_directory(self, directory_path: Path) -> bool:
        """Check if directory contains required model files"""
        return directory_path.is_dir() and all(
            (directory_path / file).exists() for file in self.REQUIRED_MODEL_FILES
        )

class TranscriptionManager:
    def __init__(self, db: Session):
        self.db = db

    # Job methods
    def create_job(self, request: CreateJobRequest, created_by: int) -> JobResponse:
        job = Job(
            created_by=created_by,
            title=request.title,
            notes=request.notes,
            status=JobStatus.CREATED
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return JobResponse.from_orm(job)

    def get_job(self, job_id: int) -> Optional[JobWithFilesResponse]:
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        return JobWithFilesResponse.from_orm(job)

    def list_jobs(self, created_by: Optional[int] = None, status: Optional[JobStatus] = None) -> List[JobResponse]:
        query = self.db.query(Job)
        if created_by is not None:
            query = query.filter(Job.created_by == created_by)
        if status is not None:
            query = query.filter(Job.status == status)
        return [JobResponse.from_orm(job) for job in query.all()]

    def update_job_status(self, job_id: int, status: JobStatus) -> Optional[JobResponse]:
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        job.status = status
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED):
            job.finished_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        return JobResponse.from_orm(job)

    def update_job_counts(self, job_id: int) -> Optional[JobResponse]:
        """Update job progress counters based on file statuses"""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        # Count files by status
        files = self.db.query(File).filter(File.job_id == job_id).all()
        job.total_count = len(files)
        job.queued_count = sum(1 for f in files if f.status == FileStatus.QUEUED)
        job.running_count = sum(1 for f in files if f.status == FileStatus.RUNNING)
        job.succeeded_count = sum(1 for f in files if f.status == FileStatus.SUCCEEDED)
        job.failed_count = sum(1 for f in files if f.status == FileStatus.FAILED)
        job.skipped_count = sum(1 for f in files if f.status == FileStatus.CANCELED)

        # Auto-update job status based on file statuses
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

        self.db.commit()
        self.db.refresh(job)
        return JobResponse.from_orm(job)

    # File methods
    def create_file(self, request: CreateFileRequest, created_by: int) -> FileResponse:
        file = File(
            job_id=request.job_id,
            created_by=created_by,
            sequence_no=request.sequence_no,
            language_hint=request.language_hint,
            status=FileStatus.QUEUED
        )
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        
        # Update job counts
        self.update_job_counts(request.job_id)
        
        return FileResponse.from_orm(file)

    def update_file_paths(self, file_id: int, source_path: str, source_name: str, source_mime: str, source_bytes: int) -> Optional[FileResponse]:
        """Update file paths and metadata after upload"""
        file = self.db.query(File).filter(File.id == file_id).first()
        if not file:
            return None

        file.source_path = source_path
        file.source_name = source_name
        file.source_mime = source_mime
        file.source_bytes = source_bytes
        file.source_uploaded_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(file)
        return FileResponse.from_orm(file)

    def get_file(self, file_id: int) -> Optional[FileWithTranscriptsResponse]:
        file = self.db.query(File).filter(File.id == file_id).first()
        if not file:
            return None
        return FileWithTranscriptsResponse.from_orm(file)

    def list_files(self, job_id: Optional[int] = None, status: Optional[FileStatus] = None) -> List[FileResponse]:
        query = self.db.query(File)
        if job_id is not None:
            query = query.filter(File.job_id == job_id)
        if status is not None:
            query = query.filter(File.status == status)
        return [FileResponse.from_orm(file) for file in query.all()]

    def update_file_status(self, file_id: int, status: FileStatus, error_message: Optional[str] = None) -> Optional[FileResponse]:
        file = self.db.query(File).filter(File.id == file_id).first()
        if not file:
            return None

        file.status = status
        if error_message is not None:
            file.error_message = error_message

        if status == FileStatus.RUNNING and not file.started_at:
            file.started_at = datetime.utcnow()
        elif status in (FileStatus.SUCCEEDED, FileStatus.FAILED, FileStatus.CANCELED):
            file.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(file)
        
        # Update job counts
        self.update_job_counts(file.job_id)
        
        return FileResponse.from_orm(file)

    # Transcript methods
    def create_transcript(self, request: CreateTranscriptRequest, created_by: int) -> TranscriptResponse:
        transcript = Transcript(
            file_id=request.file_id,
            version=request.version,
            format=request.format,
            content=request.content,
            created_by=created_by
        )
        self.db.add(transcript)
        self.db.commit()
        self.db.refresh(transcript)
        return TranscriptResponse.from_orm(transcript)

    def get_transcript(self, transcript_id: int) -> Optional[TranscriptResponse]:
        transcript = self.db.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            return None
        return TranscriptResponse.from_orm(transcript)

    def list_transcripts(self, file_id: Optional[int] = None, is_approved: Optional[bool] = None) -> List[TranscriptResponse]:
        query = self.db.query(Transcript)
        if file_id is not None:
            query = query.filter(Transcript.file_id == file_id)
        if is_approved is not None:
            query = query.filter(Transcript.is_approved == is_approved)
        return [TranscriptResponse.from_orm(t) for t in query.all()]

    def approve_transcript(self, transcript_id: int, approved_by: int) -> Optional[TranscriptResponse]:
        # Start a transaction
        transcript = self.db.query(Transcript).filter(Transcript.id == transcript_id).first()
        if not transcript:
            return None

        # First, un-approve any other transcripts for this file/format
        self.db.query(Transcript).filter(
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

        self.db.commit()
        self.db.refresh(transcript)
        return TranscriptResponse.from_orm(transcript)
