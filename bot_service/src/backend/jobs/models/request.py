from typing import Optional, List

from pydantic import BaseModel


class FileUploadInfo(BaseModel):
    source_name: str
    source_path: str
    source_mime: str
    source_bytes: int


class CreateJobRequest(BaseModel):
    files: List[FileUploadInfo]
