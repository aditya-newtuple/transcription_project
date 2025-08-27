from typing import List, Optional
from datetime import datetime
from common.models import JobStatus
from files.db_models import FileModelService
from files.models.request import CreateFileRequest
from files.models.response import FileResponse, FileWithTranscriptsResponse
from jobs.manager import JobManager

class FileManager:
    def __init__(
        self,
        file_model_service: FileModelService,
        job_manager: JobManager,
    ) -> None:
        self.file_model_service = file_model_service
        self.job_manager = job_manager
        
    def create_file(self, request: CreateFileRequest, created_by: int) -> FileResponse:
        file = self.file_model_service.create_file(request, created_by)
        return FileResponse.model_validate(file.__dict__)

    def update_file_paths(self, file_id: int, file_path: str, file_name: str, mimetype: str, bytes: int, 
                         language_hint: Optional[str] = None, duration_sec: Optional[int] = None, 
                         tags: Optional[str] = None) -> Optional[FileResponse]:
        file = self.file_model_service.update_file_paths(file_id, file_path, file_name, mimetype, bytes, 
                                                       language_hint, duration_sec, tags)
        if not file:
            return None
        return FileResponse.model_validate(file.__dict__)

    def get_file(self, file_id: int) -> Optional[FileWithTranscriptsResponse]:
        file = self.file_model_service.get_file(file_id)
        if not file:
            return None
        return FileWithTranscriptsResponse.model_validate(file.__dict__)


    def list_files(
        self,
        job_id: Optional[int] = None,
        status: Optional[JobStatus] = None,
        file_name: Optional[str] = None,
        tags: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_direction: Optional[str] = None,
        page_size: int = 10,
        page_number: int = 1
    ) -> List[FileResponse]:
        files = self.file_model_service.list_files(
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
        return [FileResponse.model_validate(file.__dict__) for file in files]

    def update_file_status(self, file_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[FileResponse]:
        file = self.file_model_service.update_file_status(file_id, status, message)
        if not file:
            return None
        return FileResponse.model_validate(file.__dict__)

    def delete_file(self, file_id: int) -> bool:
        """Delete a file and its associated transcripts.
        
        Args:
            file_id: The ID of the file to delete
            
        Returns:
            bool: True if file was found and deleted, False if file was not found
        """
        # Get the file first to get the job_id
        file = self.file_model_service.get_file(file_id)
        if not file:
            return False
            
        job_id = file.job_id
        # Delete the file (and associated transcripts via cascade)
        success = self.file_model_service.delete_file(file_id) 
        return success
