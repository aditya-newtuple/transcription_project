import shutil
import os
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form
from sqlalchemy.orm import Session

from common.configuration import Configuration
from common.logger import get_logger
from common.redis import RedisManager
from database.manager import get_db
from transcriber.models.interface import (
    CreateJobRequest, CreateFileRequest, CreateTranscriptRequest, ApproveTranscriptRequest,
    JobResponse, FileResponse, TranscriptResponse,
    JobWithFilesResponse, FileWithTranscriptsResponse,
    JobStatus, FileStatus
)
from transcriber.manager import TranscriptionManager

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/api", tags=["transcription"])

class TranscriberRestController:
    """Implements the transcriber REST controller"""

    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(self, config: Configuration) -> None:
        """Initialize the transcriber REST controller"""
        self.config = config
        self.redis_manager = RedisManager(config)
        
        # Initialize directory paths
        workspace_root = Path(os.getcwd()).resolve()
        self.etc_directory = workspace_root / "etc"
        self.input_directory = self.etc_directory / "input"
        self.output_directory = self.etc_directory / "output"
        
        # Create required directories
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure input and output directories exist with proper permissions"""
        try:
            # Create directories with proper permissions
            self.etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.input_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.output_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            
            # Verify directories are writable
            if not os.access(self.input_directory, os.W_OK):
                raise PermissionError(f"Input directory {self.input_directory} is not writable")
            if not os.access(self.output_directory, os.W_OK):
                raise PermissionError(f"Output directory {self.output_directory} is not writable")
            
            logger.info("Directories created and verified", extra={
                "input_dir": str(self.input_directory),
                "output_dir": str(self.output_directory),
                "input_writable": os.access(self.input_directory, os.W_OK),
                "output_writable": os.access(self.output_directory, os.W_OK)
            })
        except Exception as e:
            logger.error(f"Failed to create or verify directories: {str(e)}")
            raise

    def prepare(self, app: APIRouter) -> None:
        """Register API routes"""
        
        @app.post(
            "/transcriptions",
            status_code=status.HTTP_202_ACCEPTED,
            tags=["transcriber"],
            response_model=JobWithFilesResponse,
        )
        async def enqueue_transcription(
            files: List[UploadFile] = File(...),
            db: Session = Depends(get_db),
            current_user_id: int = 1
        ) -> JobWithFilesResponse:
            """Upload files and enqueue them for transcription"""
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files were provided for transcription.",
                )

            # Validate file extensions
            for file in files:
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{file.filename}' has an unsupported format. "
                        f"Allowed formats are: {', '.join(self.ALLOWED_EXTENSIONS)}",
                    )

            try:
                # Create a new job
                manager = TranscriptionManager(db)
                job = manager.create_job(
                    CreateJobRequest(
                        title="Bulk Upload",
                        notes=f"Uploaded {len(files)} files"
                    ),
                    current_user_id
                )

                # Process each file
                for idx, file in enumerate(files, 1):
                    # Save file to disk
                    unique_id = str(uuid4())
                    input_file_path = self.input_directory / f"{unique_id}_{file.filename}"
                    
                    logger.info(f"Saving uploaded file to: {input_file_path}")
                    
                    # Save uploaded file
                    with input_file_path.open("wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    if not input_file_path.exists():
                        raise FileNotFoundError(f"Failed to save uploaded file to {input_file_path}")
                    
                    logger.info(f"File saved successfully: {input_file_path}")

                    # Create file record
                    file_record = manager.create_file(
                        CreateFileRequest(
                            job_id=job.id,
                            sequence_no=idx,
                            language_hint=None
                        ),
                        current_user_id
                    )

                    # Update file record with paths
                    file_record = manager.update_file_paths(
                        file_record.id,
                        str(input_file_path),
                        file.filename,
                        file.content_type,
                        os.path.getsize(input_file_path)
                    )

                    # Enqueue job in Redis
                    self.redis_manager.enqueue_job({
                        "file_id": file_record.id,
                        "job_id": job.id,
                        "input_path": str(input_file_path),
                        "output_directory": str(self.output_directory)
                    })
                    logger.info(f"Enqueued file {file_record.id} in Redis")

                # Get updated job with files
                return manager.get_job(job.id)

            except Exception as e:
                logger.error(f"Failed to enqueue transcription jobs: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred while enqueuing jobs: {str(e)}",
                )

# Job endpoints
@router.post("/jobs", response_model=JobResponse)
def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db),
    # TODO: Get actual user ID from auth
    current_user_id: int = 1
):
    manager = TranscriptionManager(db)
    return manager.create_job(request, current_user_id)

@router.get("/jobs/{job_id}", response_model=JobWithFilesResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    manager = TranscriptionManager(db)
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    created_by: Optional[int] = None,
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    return manager.list_jobs(created_by, status)

@router.put("/jobs/{job_id}/status", response_model=JobResponse)
def update_job_status(
    job_id: int,
    status: JobStatus,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    job = manager.update_job_status(job_id, status)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# File endpoints
@router.post("/files", response_model=FileResponse)
async def create_file(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    sequence_no: Optional[int] = Form(None),
    language_hint: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    # TODO: Get actual user ID from auth
    current_user_id: int = 1
):
    manager = TranscriptionManager(db)
    
    # Create file record
    request = CreateFileRequest(
        job_id=job_id,
        sequence_no=sequence_no,
        language_hint=language_hint
    )
    file_record = manager.create_file(request, current_user_id)
    
    # TODO: Handle file upload, processing, and status updates
    # This should be done asynchronously via a worker
    
    return file_record

@router.get("/files/{file_id}", response_model=FileWithTranscriptsResponse)
def get_file(file_id: int, db: Session = Depends(get_db)):
    manager = TranscriptionManager(db)
    file = manager.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file

@router.get("/files", response_model=List[FileResponse])
def list_files(
    job_id: Optional[int] = None,
    status: Optional[FileStatus] = None,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    return manager.list_files(job_id, status)

@router.put("/files/{file_id}/status", response_model=FileResponse)
def update_file_status(
    file_id: int,
    status: FileStatus,
    error_message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    file = manager.update_file_status(file_id, status, error_message)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file

# Transcript endpoints
@router.post("/transcripts", response_model=TranscriptResponse)
def create_transcript(
    request: CreateTranscriptRequest,
    db: Session = Depends(get_db),
    # TODO: Get actual user ID from auth
    current_user_id: int = 1
):
    manager = TranscriptionManager(db)
    return manager.create_transcript(request, current_user_id)

@router.get("/transcripts/{transcript_id}", response_model=TranscriptResponse)
def get_transcript(transcript_id: int, db: Session = Depends(get_db)):
    manager = TranscriptionManager(db)
    transcript = manager.get_transcript(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript

@router.get("/transcripts", response_model=List[TranscriptResponse])
def list_transcripts(
    file_id: Optional[int] = None,
    is_approved: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    return manager.list_transcripts(file_id, is_approved)

@router.post("/transcripts/{transcript_id}/approve", response_model=TranscriptResponse)
def approve_transcript(
    transcript_id: int,
    request: ApproveTranscriptRequest,
    db: Session = Depends(get_db)
):
    manager = TranscriptionManager(db)
    transcript = manager.approve_transcript(transcript_id, request.approved_by)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript
