import os
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Query

from common.configuration import Configuration
from common.logger import get_logger
from common.models import FileStatus
from common.redis import RedisManager
from files.manager import FileManager
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileStatusResponse, FileWithTranscriptsResponse
from jobs.manager import JobManager
from jobs.models.request import CreateJobRequest

logger = get_logger(__name__)


class FilesRestController:
    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(self, file_manager: FileManager, config: Configuration) -> None:
        self.file_manager = file_manager
        self.config = config
        self.redis_manager = RedisManager(config)

    def prepare(self, app: APIRouter) -> None:
        @app.get("/files/{file_id}", tags=["files"], response_model=FileWithTranscriptsResponse)
        def get_file(
            file_id: int,
            current_user_id: int = 1
        ):
            """
            Get a file by its ID.
            """
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            return file

        @app.get("/files", tags=["files"], response_model=List[FileResponse])
        def list_files(
            job_id: Optional[int] = None,
            status: Optional[FileStatus] = None,
            page_size: int = Query(default=10, ge=1, le=50, description="Number of files to return"),
            current_user_id: int = 1
        ):
            """
            List files with pagination. Returns the most recent files first.
            
            Parameters:
            - job_id: Filter by job ID
            - status: Filter by file status
            - page_size: Number of files to return (max 50)
            """
            return self.file_manager.list_files(job_id, status, page_size)

        @app.get("/files/{file_id}/status",tags=["files"],response_model=FileStatusResponse)
        def get_file_status(
            file_id: int,
            current_user_id: int = 1
        ):
            """
            Get a file's status.
            """
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            return file.status

        @app.put("/files/{file_id}/status", tags=["files"], response_model=FileResponse)
        def update_file_status(
            file_id: int,
            status: FileStatus,
            error_message: Optional[str] = None,
            current_user_id: int = 1
        ):
            """
            Update a file's status.
            """
            file = self.file_manager.update_file_status(file_id, status, error_message)
            if not file:
                raise HTTPException(status_code=404, detail="File not found")
            return file

        @app.delete("/files/{file_id}", tags=["files"], status_code=status.HTTP_204_NO_CONTENT)
        def delete_file(
            file_id: int,
            current_user_id: int = 1
        ):
            """
            Delete a file and all its associated transcripts.
            """
            success = self.file_manager.delete_file(file_id)
            if not success:
                raise HTTPException(status_code=404, detail="File not found")
            return None  # 204 No Content response
