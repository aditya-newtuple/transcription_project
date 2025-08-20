from typing import List, Optional

from transcripts.db_models import TranscriptModelService
from transcripts.models.request import (ApproveTranscriptRequest,
                                        CreateTranscriptRequest)
from transcripts.models.response import TranscriptResponse


class TranscriptManager:
    def __init__(self, transcript_model_service: TranscriptModelService) -> None:
        self.transcript_model_service = transcript_model_service

    def create_transcript(self, request: CreateTranscriptRequest, created_by: int) -> TranscriptResponse:
        transcript = self.transcript_model_service.create_transcript(request, created_by)
        return TranscriptResponse.from_orm(transcript)

    def get_transcript(self, transcript_id: int) -> Optional[TranscriptResponse]:
        transcript = self.transcript_model_service.get_transcript(transcript_id)
        if not transcript:
            return None
        return TranscriptResponse.from_orm(transcript)

    def list_transcripts(self, file_id: Optional[int] = None, is_approved: Optional[bool] = None) -> List[TranscriptResponse]:
        transcripts = self.transcript_model_service.list_transcripts(file_id, is_approved)
        return [TranscriptResponse.from_orm(t) for t in transcripts]

    def approve_transcript(self, transcript_id: int, request: ApproveTranscriptRequest) -> Optional[TranscriptResponse]:
        transcript = self.transcript_model_service.approve_transcript(transcript_id, request.approved_by)
        if not transcript:
            return None
        return TranscriptResponse.from_orm(transcript)
