from typing import List, Optional
import os
from pathlib import Path
import time
import uuid
import time
from fastapi import HTTPException, UploadFile
from common.models import BatchStatus, JobStatus
from jobs.db_models import JobModelService, Job
from jobs.models.request import CreateJobRequest, FileUploadInfo
from jobs.models.response import (
    FilterParams,
    JobResponse,
    JobWithFilesResponse,
    PaginatedJobResponse,
)
from files.db_models import FileModelService, File  # Added File import
from files.models.request import CreateFileRequest
from transcriber.manager import TranscriberServiceManager
from transcripts.db_models import TranscriptModelService
from transcripts.models.request import CreateTranscriptRequest
from common.logger import logger
from database.manager import RedisDBService


# Constants for file upload limitations
MAX_FILE_SIZE_MB = 100  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
MAX_FILES_PER_JOB = 5  # Maximum number of files per job


class JobManager:
    def __init__(
        self, 
        job_model_service: JobModelService,
        file_model_service: FileModelService,
        transcriber_service: TranscriberServiceManager,
        transcript_model_service: TranscriptModelService,
        redis_manager: RedisDBService
    ) -> None:
        self.job_model_service = job_model_service
        self.file_model_service = file_model_service
        self.transcriber_service = transcriber_service
        self.transcript_model_service = transcript_model_service
        self.redis_manager = redis_manager

        # Set up base directories
        # In Docker, the base path is /app/backend
        # In local dev, it's the current working directory
        if os.path.exists(str(os.environ.get("WORKSPACE_ROOT"))):
            self.base_path = Path(str(os.environ.get("WORKSPACE_ROOT")))
        else:
            self.base_path = Path.cwd().resolve()
            if self.base_path.name == 'src':
                self.base_path = self.base_path.parent
            elif self.base_path.name == 'backend':
                self.base_path = self.base_path
            else:
                self.base_path = self.base_path / 'bot_service' / 'src' / 'backend'

        logger.info(f"Using base path: {self.base_path}")

        # Set up directories relative to base path
        self.etc_dir = self.base_path / "etc"
        self.input_dir = self.etc_dir / "input"
        self.output_dir = self.etc_dir / "output"

        # Create directories if they don't exist
        os.makedirs(self.etc_dir, mode=0o755, exist_ok=True)
        os.makedirs(self.input_dir, mode=0o755, exist_ok=True)
        os.makedirs(self.output_dir, mode=0o755, exist_ok=True)

        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")

    def _get_absolute_path(self, path: str | Path) -> Path:
        """Convert any path to absolute path relative to base_path if needed"""
        path = Path(path)
        if not path.is_absolute():
            path = self.base_path / path
        return path.resolve()

    async def process_uploaded_files(
        self,
        files: List[UploadFile]
    ) -> List[FileUploadInfo]:
        """
        Process uploaded files, validate them, and return file info list.
        Raises HTTPException for validation errors.
        """
        # Validate number of files
        if len(files) > MAX_FILES_PER_JOB:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_FILES_PER_JOB} files can be uploaded at once. Received {len(files)} files."
            )

        file_infos = []
        
        # Process each uploaded file
        for file in files:
            try:
                # Read file content and check size
                content = await file.read()
                file_size = len(content)

                # Validate file size
                if file_size > MAX_FILE_SIZE_BYTES:
                    # Clean up any files that were saved
                    self._cleanup_files(file_infos)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File '{file.filename}' exceeds maximum size limit of {MAX_FILE_SIZE_MB}MB. File size: {file_size / (1024 * 1024):.2f}MB"
                    )
                
                # Create a unique filename using UUID
                unique_id = str(uuid.uuid4())
                safe_filename = f"{unique_id}_{file.filename}"
                file_path = self.input_dir / safe_filename
                
                # Save the file
                with open(file_path, "wb") as f:
                    f.write(content)
                
                logger.info(f"Saved file to: {file_path}")
                
                # Create FileUploadInfo with absolute path
                file_info = FileUploadInfo(
                    source_name=file.filename,
                    source_path=str(file_path.absolute()),  # Store absolute path
                    source_mime=file.content_type,
                    source_bytes=file_size,
                )
                file_infos.append(file_info)
                
            except HTTPException:
                # Re-raise HTTP exceptions (like size limit)
                raise
            except Exception as e:
                # Clean up any files that were saved if there's an error
                self._cleanup_files(file_infos)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing file {file.filename}: {str(e)}"
                )

        return file_infos

    def _cleanup_files(self, file_infos: List[FileUploadInfo]) -> None:
        """Clean up any saved files."""
        for info in file_infos:
            try:
                path = self._get_absolute_path(info.source_path)
                if path.exists():
                    path.unlink()
                    logger.info(f"Cleaned up file: {path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {info.source_path}: {str(e)}")

    async def create_job_with_files(
        self,
        files: List[UploadFile],
        created_by: int
    ) -> JobResponse:
        """
        Create a job with the uploaded files, process them, and start transcription.
        """
        try:
            # Process uploaded files
            file_infos = await self.process_uploaded_files(files)

            # Create the job request
            job_request = CreateJobRequest(
                files=file_infos
            )

            # Create job and process files
            return self.create_job(job_request, created_by)
        except Exception as e:
            # If it's already an HTTPException, re-raise it
            if isinstance(e, HTTPException):
                raise
            # Clean up any uploaded files if job creation fails
            self._cleanup_files(file_infos if 'file_infos' in locals() else [])
            raise HTTPException(
                status_code=500,
                detail=f"Error creating job: {str(e)}"
            )

    def create_job(self, request: CreateJobRequest, created_by: int) -> JobResponse:
        # Create the job first
        job = self.job_model_service.create_job(request, created_by)
        
        # Create file records and queue them for transcription
        for file_info in request.files:
            # Create file record
            file_request = CreateFileRequest(
                job_id=job.id,
            )
            file = self.file_model_service.create_file(file_request, created_by)

            # Update file paths with absolute path and additional metadata
            file = self.file_model_service.update_file_paths(
                file_id=file.id,
                path=str(self._get_absolute_path(file_info.source_path)),
                file_name=file_info.source_name,
                mimetype=file_info.source_mime,
                bytes=file_info.source_bytes,
                tags="audio,transcription"  # Default tags
            )

            # Queue the file for transcription
            self.queue_file_for_transcription(file.id, created_by, file_info.source_path)

        # Update job status to QUEUED since files are queued for processing
        updated_job = self.job_model_service.update_job_status(job.id, BatchStatus.QUEUED)
        return JobResponse.model_validate(updated_job.__dict__)

    def queue_file_for_transcription(self, file_id: int, created_by: int, source_path: str) -> None:
        """Queue a file for transcription processing."""
        try:
            # Get absolute path
            abs_path = str(self._get_absolute_path(source_path))
            
            # Prepare job data for the queue
            job_data = {
                "file_id": file_id,
                "created_by": created_by,
                "source_path": abs_path,  # Use absolute path
                "action": "transcribe"
            }
            
            logger.info(f"Queueing file for transcription: {abs_path}")
            
            # Add to Redis queue
            self.redis_manager.enqueue_job(job_data)
            
        except Exception as e:
            # If queueing fails, mark the file as failed
            self.file_model_service.update_file_status(
                file_id, 
                JobStatus.FAILED,
                message=f"Failed to queue for transcription: {str(e)}"
            )
            raise

    def process_queued_file(self, file_id: int, created_by: int, source_path: str) -> None:
        """Process a queued file for transcription."""
        try:
            # Get absolute path
            input_file = self._get_absolute_path(source_path)
            
            # Verify file exists
            if not input_file.exists():
                raise FileNotFoundError(f"Source file not found: {input_file}")

            logger.info(f"Processing file: {input_file}")

            # Update file status to RUNNING
            self.file_model_service.update_file_status(file_id, JobStatus.RUNNING)
            
            try:
                transcription_start_time = time.time()
                
                # Perform transcription
                logger.info(f"Starting transcription for file {file_id}")
                text_file_path, subtitle_file_path, transcription_info = self.transcriber_service.transcribe_file(
                    input_file=input_file,
                    output_directory=self.output_dir
                )
                
                logger.info(f"Transcription completed. Text file: {text_file_path}, SRT file: {subtitle_file_path}")
                
                # Verify output files exist
                if not text_file_path.exists():
                    raise FileNotFoundError(f"Text output file not found: {text_file_path}")
                if not subtitle_file_path.exists():
                    raise FileNotFoundError(f"Subtitle output file not found: {subtitle_file_path}")

                # Create single transcript record with both formats
                try:
                    # Read both transcript contents
                    with open(text_file_path, 'r', encoding='utf-8') as f:
                        txt_content = f.read()
                        if not txt_content.strip():
                            raise ValueError("Empty text transcript generated")
                    
                    with open(subtitle_file_path, 'r', encoding='utf-8') as f:
                        srt_content = f.read()
                        if not srt_content.strip():
                            raise ValueError("Empty SRT transcript generated")
                    
                    # Calculate actual transcription duration (from when we started processing)
                    actual_transcription_duration = int(time.time() - transcription_start_time)
                    
                    logger.info(f"Creating transcript record for file {file_id} with both TXT and SRT content")
                    transcript_request = CreateTranscriptRequest(
                        file_id=file_id,
                        version=1,
                        text_content=txt_content,
                        srt_content=srt_content,
                        language_hint=transcription_info.language,
                        transcription_process_duration=actual_transcription_duration,
                        transcription_model=self.transcriber_service.get_model_name(),
                        message="Transcription completed successfully with both TXT and SRT formats"
                    )

                    self.transcript_model_service.create_transcript(transcript_request, created_by)

                    logger.info(f"Transcript record created for file {file_id} with both formats and metadata")

                except Exception as transcript_error:
                    logger.error(f"Failed to save transcripts for file {file_id}: {str(transcript_error)}")
                    raise RuntimeError(f"Failed to save transcripts: {str(transcript_error)}")

                # Update file status to SUCCEEDED
                self.file_model_service.update_file_status(file_id, JobStatus.SUCCEEDED)
                
                logger.info(f"Successfully processed file {file_id}")
                
            except Exception as process_error:
                logger.error(f"Failed to process file {file_id}: {str(process_error)}")
                self.file_model_service.update_file_status(
                    file_id, 
                    JobStatus.FAILED,
                    message=str(process_error)
                )
                raise
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to process file {file_id}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            # Update file status to FAILED with error message
            self.file_model_service.update_file_status(
                file_id, 
                JobStatus.FAILED,
                message=str(e)
            )
            raise RuntimeError(error_msg)

    def get_job(self, job_id: int) -> Optional[JobWithFilesResponse]:
        """Get a job by ID with its files."""
        job = self.job_model_service.get_job(job_id)
        if not job:
            return None
        return JobWithFilesResponse.model_validate(job.__dict__)

    def list_jobs(
        self,
        created_by: Optional[int] = None,
        status: Optional[BatchStatus] = None,
        file_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_direction: Optional[str] = "desc",
        page_size: int = 10,
        page_number: int = 1,
    ) -> PaginatedJobResponse:
        """
        List jobs with advanced filtering, sorting, and pagination.
        """
        # Fetch jobs and total count from the database service
        jobs, total_count = self.job_model_service.list_jobs(
            created_by=created_by,
            status=status,
            file_name=file_name,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_direction=sort_direction,
            page_size=page_size,
            page_number=page_number,
        )

        # Create the response object
        return PaginatedJobResponse(
            data=[JobResponse.model_validate(job) for job in jobs],
            page=page_number,
            page_size=page_size,
            total_count=total_count,
            sort_by=sort_by,
            order=sort_direction,
            filters=FilterParams(
                search_query=file_name,
                status=status,
                tags=tags,
                created_by=created_by,
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
            ),
        )

    def update_job_status(self, job_id: int, status: BatchStatus) -> Optional[JobResponse]:
        job = self.job_model_service.update_job_status(job_id, status)
        if not job:
            return None
        return JobResponse.model_validate(job.__dict__)

    def update_job_counts(self, job_id: int) -> Optional[JobResponse]:
        """Update job status based on its files' statuses."""
        job = self.job_model_service.update_job_counts(job_id)
        if not job:
            return None
        return JobResponse.model_validate(job.__dict__)

