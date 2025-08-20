from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from transcripts.manager import TranscriptManager
from transcripts.models.request import (ApproveTranscriptRequest,
                                        CreateTranscriptRequest)
from transcripts.models.response import TranscriptResponse


class TranscriptsRestController:
    def __init__(self, transcript_manager: TranscriptManager):
        self.transcript_manager = transcript_manager

    def prepare(self, app: APIRouter) -> None:
        @app.post("/transcripts",tags=["transcripts"], response_model=TranscriptResponse)
        def create_transcript(
            request: CreateTranscriptRequest,
            current_user_id: int = 1
        ):
            return self.transcript_manager.create_transcript(request, current_user_id)

        @app.get("/transcripts/{transcript_id}", tags=["transcripts"], response_model=TranscriptResponse)
        def get_transcript(transcript_id: int):
            transcript = self.transcript_manager.get_transcript(transcript_id)
            if not transcript:
                raise HTTPException(status_code=404, detail="Transcript not found")
            return transcript

        @app.get("/transcripts", tags=["transcripts"], response_model=List[TranscriptResponse])
        def list_transcripts(
            file_id: Optional[int] = None,
            is_approved: Optional[bool] = None,
        ):
            return self.transcript_manager.list_transcripts(file_id, is_approved)

        @app.post("/transcripts/{transcript_id}/approve", tags=["transcripts"], response_model=TranscriptResponse)
        def approve_transcript(
            transcript_id: int,
            request: ApproveTranscriptRequest,
        ):
            transcript = self.transcript_manager.approve_transcript(transcript_id, request)
            if not transcript:
                raise HTTPException(status_code=404, detail="Transcript not found")
            return transcript
