import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from common.configuration import Configuration
from auth.deps import get_current_user
from common.models import JobStatus
from files.manager import FileManager
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileStatusResponse, FileWithTranscriptsResponse, PaginatedFileResponse


class FilesRestController():
    def __init__(self, file_manager: FileManager, config: Configuration) -> None:
        self.file_manager = file_manager
        self.config = config

    def prepare(self, app: APIRouter) -> None:
        @app.get("/files/{file_id}", tags=["files"], response_model=FileWithTranscriptsResponse)
        def get_file(file_id: int) -> FileWithTranscriptsResponse:
            """
            Get a file by its ID.
            """
            file = self.file_manager.get_file(file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            return file

        @app.get("/files", tags=["files"], response_model=PaginatedFileResponse)
        def list_files(
            job_id: Optional[int] = Query(default=None, description="Filter by job ID"),
            status: Optional[JobStatus] = Query(default=None, description="Filter by job status"),
            file_name: Optional[str] = Query(default=None, description="Search by file name (partial match)"),
            tags: Optional[str] = Query(default=None, description="Filter by tags (supports multiple)"),
            date_from: Optional[datetime] = Query(default=None, description="Filter by upload date range (start date)"),
            date_to: Optional[datetime] = Query(default=None, description="Filter by upload date range (end date)"),
            sort_by: Optional[str] = Query(default=None, description="Sort by 'file_name' or 'status'"),
            sort_direction: Optional[str] = Query(default="desc", description="Sort direction: 'asc' or 'desc'"),
            page_size: int = Query(default=10, ge=1, le=50, description="Number of files to return"),
            page_number: int = Query(default=1, ge=1, description="Page number to return"),
        ) -> PaginatedFileResponse:
            """
            List files with search, filtering, sorting, and pagination.
            """
            return self.file_manager.list_files(
                job_id=job_id,
                status=status,
                file_name=file_name,
                tags=tags,
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page_size=page_size,
                page_number=page_number
            )


        @app.get("/files/{file_id}/status", tags=["files"], response_model=FileStatusResponse)
        def get_file_status(file_id: int) -> FileStatusResponse:
            """
            Get the status of a file.
            """
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
            """
            Update the status of a file.
            """
            file = self.file_manager.update_file_status(file_id, status, message)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
            return file

        @app.delete("/files/{file_id}", tags=["files"])
        def delete_file(file_id: int) -> None:
            """
            Delete a file by its ID.
            """
            if not self.file_manager.delete_file(file_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File {file_id} not found",
                )
