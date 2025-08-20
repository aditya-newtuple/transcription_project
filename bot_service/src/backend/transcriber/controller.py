import shutil
import os
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from common.configuration import Configuration
from common.logger import get_logger
from common.redis import RedisManager
from transcriber.manager import TranscriberManager
from transcriber.models.interface import (
    BulkTranscriptionRequestResponse,
    JobStatusResponse,
)
from transcriber.db_models import TranscriptionJob

logger = get_logger(__name__)

class TranscriberRestController:
    """Implements the transcriber REST controller"""

    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(self, config: Configuration) -> None:
        """Initialize the transcriber REST controller"""
        self.config = config
        self.transcriber_manager = TranscriberManager(config)
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
            self.etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.input_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.output_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            logger.info("Directories created/verified")
        except Exception as e:
            logger.error(f"Failed to create required directories: {str(e)}")
            raise

    def prepare(self, app: APIRouter) -> None:
        """Register API routes"""
        
        @app.post(
            "/transcriptions",
            status_code=status.HTTP_202_ACCEPTED,
            tags=["transcriber"],
            response_model=BulkTranscriptionRequestResponse,
        )
        async def enqueue_transcription(
            files: List[UploadFile] = File(...),
        ) -> BulkTranscriptionRequestResponse:
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

            batch_id = str(uuid4())
            job_ids = []

            try:
                # Process each file
                for file in files:
                    # Save file to disk
                    job_id = str(uuid4())
                    input_file_path = self.input_directory / f"{job_id}_{file.filename}"
                    with input_file_path.open("wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                    # Create job in database
                    job_id = self.transcriber_manager.create_job(
                        file_path=str(input_file_path),
                        output_formats=["txt", "srt"]
                    )
                    job_ids.append(job_id)

                    # Enqueue job in Redis
                    self.redis_manager.enqueue_job({
                        "job_id": job_id,
                        "file_path": str(input_file_path),
                        "output_formats": ["txt", "srt"],
                        "batch_id": batch_id
                    })

                return BulkTranscriptionRequestResponse(
                    batch_id=batch_id,
                    job_ids=job_ids,
                )

            except Exception as e:
                logger.error(f"Failed to enqueue transcription jobs: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred while enqueuing jobs: {str(e)}",
                )

        @app.get(
            "/jobs/{job_id}",
            status_code=status.HTTP_200_OK,
            tags=["transcriber"],
            response_model=JobStatusResponse,
        )
        async def get_job_status(job_id: str) -> JobStatusResponse:
            """Get status of a transcription job"""
            try:
                job = self.transcriber_manager.db_session.query(TranscriptionJob).filter(
                    TranscriptionJob.id == job_id
                ).first()
                
                if not job:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Job with id {job_id} not found.",
                    )

                return JobStatusResponse(
                    id=str(job.id),
                    batch_id=str(job.batch_id) if job.batch_id else None,
                    status=job.status,
                    original_filename=job.original_filename,
                    processed_file_path=job.processed_file_path,
                    output_file_path=job.output_file_path,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            except Exception as e:
                logger.error(f"Failed to get job status: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred while getting job status: {str(e)}",
                )
