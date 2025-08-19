from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Response model for transcription endpoint"""
    message: str = Field(..., description="Status message")
    text_file_path: str = Field(..., description="Path to the generated text file")
    subtitle_file_path: str = Field(..., description="Path to the generated subtitle file")
    detected_language: str = Field(..., description="Detected language of the audio")
    language_confidence: float = Field(..., ge=0, le=1, description="Confidence score of language detection") 