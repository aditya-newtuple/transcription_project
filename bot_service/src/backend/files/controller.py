import os
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response
from common.configuration import Configuration
from auth.deps import get_current_user
from common.models import JobStatus
from files.manager import FileManager
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileStatusResponse, FileWithTranscriptsResponse


class FilesRestController():
    def __init__(self, file_manager: FileManager, config: Configuration) -> None:
        self.file_manager = file_manager
        self.config = config

    def prepare(self, app: APIRouter) -> None:
        @app.get("/files/{file_id}", tags=["files"], response_model=FileWithTranscriptsResponse)
        def get_file(file_id: int) -> FileWithTranscriptsResponse:
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            return file

        @app.get("/files", tags=["files"], response_model=List[FileResponse])
        def list_files(
            job_id: Optional[int] = None,
            status: Optional[JobStatus] = None,
            page_size: int = 10,
        ) -> List[FileResponse]:
            return self.file_manager.list_files(job_id, status, page_size)

        @app.get("/files/{file_id}/status", tags=["files"], response_model=FileStatusResponse)
        def get_file_status(file_id: int) -> FileStatusResponse:
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            return FileStatusResponse(
                status=file.status,
                message=file.message,
                queued_at=file.queued_at,
                started_at=file.started_at,
                finished_at=file.finished_at,
            )

        @app.put("/files/{file_id}/status", tags=["files"], response_model=FileResponse)
        def update_file_status(
            file_id: int,
            status: JobStatus,
            message: Optional[str] = None,
        ) -> FileResponse:
            file = self.file_manager.update_file_status(file_id, status, message)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            return file

        @app.delete("/files/{file_id}", tags=["files"])
        def delete_file(file_id: int) -> None:
            if not self.file_manager.delete_file(file_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )

        @app.get("/files/{file_id}/download", tags=["files"])
        def download_file(file_id: int) -> Response:
            """Download/serve a file by its ID"""
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            
            file_path = Path(file.path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found on disk: {file.path}",
                )
            
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Return file with appropriate headers
            return Response(
                content=content,
                media_type=file.mime_type,
                headers={
                    "Content-Disposition": f"inline; filename={file.source_name}",
                    "Content-Length": str(len(content))
                }
            )
