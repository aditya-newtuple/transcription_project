from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from transcripts.manager import TranscriptManager
from transcripts.models.request import (ApproveTranscriptRequest,
                                      CreateTranscriptRequest)
from transcripts.models.response import TranscriptResponse


class TranscriptsRestController:
    def __init__(self, transcript_manager: TranscriptManager):
        self.transcript_manager = transcript_manager

    def prepare(self, app: APIRouter) -> None:
        @app.get("/transcripts/{transcript_id}", tags=["transcripts"], response_model=TranscriptResponse)
        def get_transcript(transcript_id: int):
            """
            Get a transcript by its ID.
            """
            transcript = self.transcript_manager.get_transcript(transcript_id)
            if not transcript:
                raise HTTPException(status_code=404, detail="Transcript not found")
            return transcript

        @app.get("/transcripts", tags=["transcripts"], response_model=List[TranscriptResponse])
        def list_transcripts(
            file_id: Optional[int] = None,
            is_approved: Optional[bool] = None,
            page_size: int = Query(default=10, ge=1, le=50, description="Number of transcripts to return"),
        ):
            """
            List transcripts with pagination. Returns the most recent transcripts first.
            
            Parameters:
            - file_id: Filter by file ID
            - is_approved: Filter by approval status
            - page_size: Number of transcripts to return (max 50)
            """
            return self.transcript_manager.list_transcripts(file_id, is_approved, page_size)

        @app.put("/transcripts/{transcript_id}/approve", tags=["transcripts"], response_model=TranscriptResponse)
        def approve_transcript(
            transcript_id: int,
            request: ApproveTranscriptRequest,
        ):
            """
            Approve a transcript by its ID.
            """
            transcript = self.transcript_manager.approve_transcript(transcript_id, request)
            if not transcript:
                raise HTTPException(status_code=404, detail="Transcript not found")
            return transcript
