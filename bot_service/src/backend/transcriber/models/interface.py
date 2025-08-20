from pathlib import Path
from typing import Optional, List
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


class BulkTranscriptionRequestResponse(BaseModel):
    """Response model for the asynchronous transcription request"""
    batch_id: str = Field(..., description="A unique ID for the batch of transcription jobs")
    job_ids: List[str] = Field(..., description="A list of job IDs for each uploaded file")


class JobStatusResponse(BaseModel):
    """Response model for the job status endpoint"""
    id: str
    batch_id: str
    status: str
    original_filename: str
    processed_file_path: Optional[str] = None
    output_file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime