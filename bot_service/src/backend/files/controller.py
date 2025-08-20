import os
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from common.configuration import Configuration
from common.logger import get_logger
from common.models import FileStatus
from common.redis import RedisManager
from files.manager import FileManager
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileWithTranscriptsResponse
from jobs.manager import JobManager
from jobs.models.request import CreateJobRequest

logger = get_logger(__name__)


class FilesRestController:
    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(self, file_manager: FileManager, config: Configuration) -> None:
        self.file_manager = file_manager
        self.config = config
        self.redis_manager = RedisManager(config)
        
        workspace_root = Path(os.getcwd()).resolve()
        self.etc_directory = workspace_root / "etc"
        self.input_directory = self.etc_directory / "input"
        self.output_directory = self.etc_directory / "output"
        
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        try:
            self.etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.input_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.output_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            
            if not os.access(self.input_directory, os.W_OK):
                raise PermissionError(f"Input directory {self.input_directory} is not writable")
            if not os.access(self.output_directory, os.W_OK):
                raise PermissionError(f"Output directory {self.output_directory} is not writable")
            
            logger.info("Directories created and verified")
        except Exception as e:
            logger.error(f"Failed to create or verify directories: {str(e)}")
            raise

    def prepare(self, app: APIRouter) -> None:
        @app.post(
            "/files/upload",
            status_code=status.HTTP_202_ACCEPTED,
            tags=["files"],
        )
        async def enqueue_transcription(
            files: List[UploadFile] = File(...),
            current_user_id: int = 1
        ):
            job_manager = JobManager(self.file_manager)
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files were provided for transcription.",
                )

            for file in files:
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{file.filename}' has an unsupported format. "
                        f"Allowed formats are: {', '.join(self.ALLOWED_EXTENSIONS)}",
                    )

            try:
                job = job_manager.create_job(
                    CreateJobRequest(
                        title="Bulk Upload",
                        notes=f"Uploaded {len(files)} files"
                    ),
                    current_user_id
                )

                for idx, file in enumerate(files, 1):
                    unique_id = str(uuid4())
                    input_file_path = self.input_directory / f"{unique_id}_{file.filename}"
                    
                    with input_file_path.open("wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    if not input_file_path.exists():
                        raise FileNotFoundError(f"Failed to save uploaded file to {input_file_path}")

                    file_record = self.file_manager.create_file(
                        CreateFileRequest(
                            job_id=job.id,
                            sequence_no=idx,
                            language_hint=None
                        ),
                        current_user_id
                    )

                    file_record = self.file_manager.update_file_paths(
                        file_record.id,
                        str(input_file_path),
                        file.filename,
                        file.content_type,
                        os.path.getsize(input_file_path)
                    )

                    self.redis_manager.enqueue_job({
                        "file_id": file_record.id,
                        "job_id": job.id,
                        "input_path": str(input_file_path),
                        "output_directory": str(self.output_directory)
                    })
                    logger.info(f"Enqueued file {file_record.id} in Redis")

                return job_manager.get_job(job.id)

            except Exception as e:
                logger.error(f"Failed to enqueue transcription jobs: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred while enqueuing jobs: {str(e)}",
                )

        @app.post("/files", tags=["files"], response_model=FileResponse)
        async def create_file(
            file: UploadFile = File(...),
            job_id: int = Form(...),
            sequence_no: Optional[int] = Form(None),
            language_hint: Optional[str] = Form(None),
            current_user_id: int = 1
        ):
            request = CreateFileRequest(
                job_id=job_id,
                sequence_no=sequence_no,
                language_hint=language_hint
            )
            file_record = self.file_manager.create_file(request, current_user_id)
            return file_record

        @app.get("/files/{file_id}", tags=["files"], response_model=FileWithTranscriptsResponse)
        def get_file(
            file_id: int,
            current_user_id: int = 1
        ):
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            return file

        @app.get("/files", tags=["files"], response_model=List[FileResponse])
        def list_files(
            job_id: Optional[int] = None,
            status: Optional[FileStatus] = None,
            current_user_id: int = 1
        ):
            return self.file_manager.list_files(job_id, status)

        @app.put("/files/{file_id}/status", tags=["files"], response_model=FileResponse)
        def update_file_status(
            file_id: int,
            status: FileStatus,
            error_message: Optional[str] = None,
            current_user_id: int = 1
        ):
            file = self.file_manager.update_file_status(file_id, status, error_message)
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            return file
