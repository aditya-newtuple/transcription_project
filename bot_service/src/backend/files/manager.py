from typing import List, Optional

from common.models import FileStatus
from files.db_models import FileModelService
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileWithTranscriptsResponse
from jobs.manager import JobManager


class FileManager:
    def __init__(self, file_model_service: FileModelService, job_manager: JobManager) -> None:
        self.file_model_service = file_model_service
        self.job_manager = job_manager

    def create_file(self, request: CreateFileRequest, created_by: int) -> FileResponse:
        file = self.file_model_service.create_file(request, created_by)
        self.job_manager.update_job_counts(file.job_id)
        return FileResponse.from_orm(file)

    def update_file_paths(self, file_id: int, source_path: str, source_name: str, source_mime: str, source_bytes: int) -> Optional[FileResponse]:
        file = self.file_model_service.update_file_paths(file_id, source_path, source_name, source_mime, source_bytes)
        if not file:
            return None
        return FileResponse.from_orm(file)

    def get_file(self, file_id: int) -> Optional[FileWithTranscriptsResponse]:
        file = self.file_model_service.get_file(file_id)
        if not file:
            return None
        return FileWithTranscriptsResponse.from_orm(file)

    def list_files(self, job_id: Optional[int] = None, status: Optional[FileStatus] = None) -> List[FileResponse]:
        files = self.file_model_service.list_files(job_id, status)
        return [FileResponse.from_orm(file) for file in files]

    def update_file_status(self, file_id: int, status: FileStatus, error_message: Optional[str] = None) -> Optional[FileResponse]:
        file = self.file_model_service.update_file_status(file_id, status, error_message)
        if not file:
            return None
        self.job_manager.update_job_counts(file.job_id)
        return FileResponse.from_orm(file)
