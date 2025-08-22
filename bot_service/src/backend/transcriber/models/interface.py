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