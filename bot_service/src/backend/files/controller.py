import os
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
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
        def download_file(file_id: int, request: Request) -> Response:
            """Download/serve a file by its ID with support for range requests"""
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
            
            file_size = file_path.stat().st_size
            
            # Check for range request
            range_header = request.headers.get('range')
            if range_header:
                try:
                    # Parse range header (e.g., "bytes=0-1023")
                    range_str = range_header.replace('bytes=', '')
                    start, end = range_str.split('-')
                    start = int(start)
                    end = int(end) if end else file_size - 1
                    
                    # Validate range
                    if start >= file_size or end >= file_size or start > end:
                        raise HTTPException(
                            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                            detail="Invalid range request"
                        )
                    
                    # Read requested range
                    with open(file_path, 'rb') as f:
                        f.seek(start)
                        content = f.read(end - start + 1)
                    
                    # Return partial content
                    return Response(
                        content=content,
                        media_type=file.mime_type,
                        status_code=status.HTTP_206_PARTIAL_CONTENT,
                        headers={
                            "Content-Range": f"bytes {start}-{end}/{file_size}",
                            "Content-Length": str(len(content)),
                            "Accept-Ranges": "bytes",
                            "Content-Disposition": f"inline; filename={file.source_name}"
                        }
                    )
                except (ValueError, IndexError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid range header format"
                    )
            else:
                # No range request - return full file
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                return Response(
                    content=content,
                    media_type=file.mime_type,
                    headers={
                        "Content-Length": str(len(content)),
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": f"inline; filename={file.source_name}"
                    }
                )
