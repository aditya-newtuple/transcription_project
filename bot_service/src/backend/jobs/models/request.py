from typing import Optional, List

from pydantic import BaseModel


class FileUploadInfo(BaseModel):
    source_name: str
    source_path: str
    source_mime: str
    source_bytes: int
    sequence_no: Optional[int] = None
    language_hint: Optional[str] = None


class CreateJobRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    files: List[FileUploadInfo]
