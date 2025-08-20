import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Callable, Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Request
from common.logger import logger
from common.redis import RedisManager
from jobs.db_models import JobModelService
from jobs.models.request import CreateJobRequest
from jobs.models.response import JobResponse
from files.db_models import FileModelService
from files.models.request import CreateFileRequest
from transcriber.manager import TranscriberManager


class TranscriberRestController:
    """Implements the transcriber REST controller"""

    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(
        self,
        transcriber_manager: Optional[TranscriberManager],  # may be None; prefer DI
        redis_manager: RedisManager,
        job_model_service: JobModelService,
        file_model_service: FileModelService,
        get_transcriber_dep: Optional[Callable[[Request], TranscriberManager]] = None,
    ) -> None:
        """
        Initialize the transcriber REST controller.

        Args:
            transcriber_manager: Optional concrete instance (legacy). Prefer DI via get_transcriber_dep.
            redis_manager: Redis manager for job queuing
            job_model_service: Service for job models
            file_model_service: Service for file models
            get_transcriber_dep: Dependency function (Request -> TranscriberManager).
                                 Typically: lambda req: req.app.state.transcriber_manager
        """
        self.transcriber_manager = transcriber_manager
        self.redis_manager = redis_manager
        self.job_model_service = job_model_service
        self.file_model_service = file_model_service
        self.get_transcriber_dep = get_transcriber_dep

        # Initialize directory paths
        workspace_root = Path.cwd().resolve()
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

            logger.info(
                "Directories created/verified",
                extra={
                    "input_path": str(self.input_directory),
                    "output_path": str(self.output_directory),
                },
            )

        except Exception as error:
            logger.error("Failed to create required directories", exc_info=error)
            raise RuntimeError(f"Failed to create required directories: {error}")

    # Fallback provider if caller didn't supply get_transcriber_dep
    @staticmethod
    def _require_transcriber_from_state(req: Request) -> TranscriberManager:
        tm = getattr(req.app.state, "transcriber_manager", None)
        if tm is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transcriber service is not initialized",
            )
        return tm

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the transcriber REST controller by registering routes.

        Args:
            app: FastAPI router instance to register routes on
        """

        # Choose the dependency function (prefer the one injected from main.py)
        provider = self.get_transcriber_dep or self._require_transcriber_from_state
        TranscriberDep = Annotated[TranscriberManager, Depends(provider)]

        @app.post(
            "/transcriptions",
            status_code=status.HTTP_201_CREATED,
            tags=["transcriber"],
            response_model=JobResponse,
        )
        def create_transcription_job(
            files: List[UploadFile] = File(...),
            request: CreateJobRequest = Depends(),
            transcriber: TranscriberDep = None,  # injected singleton (available if needed)
        ) -> JobResponse:
            """
            Upload one or more audio/video files to start a transcription job.
            """
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files were provided for transcription.",
                )

            # Validate extensions
            for f in files:
                file_ext = Path(f.filename).suffix.lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    logger.error("Unsupported file format attempted", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"File '{f.filename}' has an unsupported format. "
                            f"Allowed formats are: {', '.join(self.ALLOWED_EXTENSIONS)}"
                        ),
                    )

            try:
                # Create a job in the database (TODO: use real user id)
                job = self.job_model_service.create_job(request, created_by=1)

                # Ensure directories exist before processing
                self._ensure_directories()

                for index, f in enumerate(files):
                    # Create DB record
                    file_request = CreateFileRequest(job_id=job.id, sequence_no=index + 1)
                    db_file = self.file_model_service.create_file(file_request, created_by=1)

                    # Save the uploaded file to input dir with unique name
                    unique_filename = f"{uuid.uuid4()}{Path(f.filename).suffix}"
                    input_file_path = self.input_directory / unique_filename

                    with input_file_path.open("wb") as buffer:
                        shutil.copyfileobj(f.file, buffer)

                    # Get size (file stream is at end; .tell() returns bytes written)
                    size_bytes = f.file.tell()

                    # Update DB record with path & metadata
                    self.file_model_service.update_file_paths(
                        file_id=db_file.id,
                        source_path=str(input_file_path),
                        source_name=f.filename,
                        source_mime=f.content_type,
                        source_bytes=size_bytes,
                    )

                    logger.info(
                        "Audio file saved for transcription",
                        extra={
                            "input_path": str(input_file_path),
                            "original_name": f.filename,
                            "job_id": job.id,
                            "file_id": db_file.id,
                        },
                    )

                    # Enqueue job in Redis (use your queueing layer / worker)
                    job_data = {
                        "job_id": job.id,
                        "file_id": db_file.id,
                        "input_path": str(input_file_path),
                        "output_directory": str(self.output_directory),
                    }
                    self.redis_manager.enqueue_job(job_data)

                # Update job counters & return
                self.job_model_service.update_job_counts(job.id)
                updated_job = self.job_model_service.get_job(job.id)
                return updated_job

            except Exception as error:
                logger.error("Failed to create transcription job", exc_info=error)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred during job creation: {str(error)}",
                )