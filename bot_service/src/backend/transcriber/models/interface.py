from pathlib import Path
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """Detailed result for a single transcribed file"""
    text_file_path: str = Field(..., description="Path to the generated text file")
    subtitle_file_path: str = Field(..., description="Path to the generated subtitle file")
    detected_language: str = Field(..., description="Detected language of the audio")
    language_confidence: float = Field(..., ge=0, le=1, description="Confidence score of language detection") 


class BulkTranscriptionResponse(BaseModel):
    """Response model for bulk transcription endpoint"""
    message: str = Field(..., description="Overall status message")
    results: List[TranscriptionResult] = Field(..., description="List of transcription results for each file")


from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    CREATED = 'created'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'

class FileStatus(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'

class TranscriptFormat(str, Enum):
    TXT = 'txt'
    SRT = 'srt'

# Request Models
class CreateJobRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None

class CreateFileRequest(BaseModel):
    job_id: int
    sequence_no: Optional[int] = None
    language_hint: Optional[str] = None

class CreateTranscriptRequest(BaseModel):
    file_id: int
    format: TranscriptFormat
    content: str
    version: Optional[int] = Field(default=1, ge=1)

class ApproveTranscriptRequest(BaseModel):
    approved_by: int

# Response Models
class JobResponse(BaseModel):
    id: int
    created_by: int
    status: JobStatus
    title: Optional[str]
    notes: Optional[str]
    total_count: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_summary: Optional[str]

    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    id: int
    job_id: int
    created_by: int
    sequence_no: Optional[int]
    source_name: Optional[str]
    source_path: Optional[str]
    source_mime: Optional[str]
    source_bytes: Optional[int]
    source_uploaded_at: datetime
    source_deleted_at: Optional[datetime]
    status: FileStatus
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    language_hint: Optional[str]
    duration_sec: Optional[int]

    class Config:
        from_attributes = True

class TranscriptResponse(BaseModel):
    id: int
    file_id: int
    version: int
    format: TranscriptFormat
    content: Optional[str]
    created_at: datetime
    created_by: Optional[int]
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    is_approved: bool

    class Config:
        from_attributes = True

class JobWithFilesResponse(JobResponse):
    files: List[FileResponse] = []

class FileWithTranscriptsResponse(FileResponse):
    transcripts: List[TranscriptResponse] = []