import shutil
import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from common.logger import logger
from transcriber.manager import TranscriberServiceManager
from transcriber.models.interface import BulkTranscriptionResponse, TranscriptionResult


class TranscriberRestController:
    """Implements the transcriber REST controller"""

    ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpeg4"}

    def __init__(self, transcriber_service_manager: TranscriberServiceManager) -> None:
        """
        Initialize the transcriber REST controller.
        
        Args:
            transcriber_service_manager: Service manager for transcription operations
        """
        self.transcriber_service_manager = transcriber_service_manager
        
        # Initialize directory paths
        workspace_root = Path(os.getcwd()).resolve()
        self.etc_directory = workspace_root / "etc"
        self.input_directory = self.etc_directory / "input"
        self.output_directory = self.etc_directory / "output"
        
        # Create required directories
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure input and output directories exist with proper permissions"""
        try:
            self.etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.input_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            self.output_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            
            logger.info("Directories created/verified", 
                       extra={
                           "input_path": str(self.input_directory),
                           "output_path": str(self.output_directory)
                       })
                       
        except Exception as error:
            logger.error("Failed to create required directories", exc_info=error)
            raise RuntimeError(f"Failed to create required directories: {error}")

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the transcriber REST controller by registering routes.
        
        Args:
            app: FastAPI router instance to register routes on
        """
        @app.post(
            "/transcribe",
            status_code=status.HTTP_200_OK,
            tags=["transcriber"],
            response_model=BulkTranscriptionResponse
        )
        async def transcribe(
            files: List[UploadFile] = File(...)
        ) -> BulkTranscriptionResponse:
            """
            Upload one or more audio/video files and transcribe them.
            
            Args:
                files: List of audio/video files to transcribe
                
            Returns:
                Bulk transcription response with results for each file
            """
            if not files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files were provided for transcription."
                )

            for file in files:
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    logger.error("Unsupported file format attempted", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{file.filename}' has an unsupported format. "
                               f"Allowed formats are: {', '.join(self.ALLOWED_EXTENSIONS)}"
                    )
            
            transcription_results = []
            
            try:
                # Ensure directories exist before processing
                self._ensure_directories()

                for file in files:
                    # Save the uploaded file
                    input_file_path = self.input_directory / file.filename
                    with input_file_path.open("wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    logger.info("Audio file saved for transcription", 
                              extra={
                                  "input_path": str(input_file_path),
                                  "original_name": file.filename
                              })

                    # Transcribe the file
                    text_file_path, subtitle_file_path, transcription_info = self.transcriber_service_manager.transcribe_file(
                        input_file=input_file_path,
                        output_directory=self.output_directory,
                        beam_size=5,
                        use_vad=True
                    )

                    # Create result object
                    result = TranscriptionResult(
                        text_file_path=str(text_file_path),
                        subtitle_file_path=str(subtitle_file_path),
                        detected_language=transcription_info.language,
                        language_confidence=transcription_info.language_probability
                    )
                    transcription_results.append(result)

                return BulkTranscriptionResponse(
                    message="All files transcribed successfully",
                    results=transcription_results
                )

            except Exception as error:
                logger.error("Transcription failed", exc_info=error)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred during transcription: {error}"
                )