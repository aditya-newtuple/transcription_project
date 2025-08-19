import shutil
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from common.logger import logger
from transcriber.manager import TranscriberServiceManager
from transcriber.models.interface import TranscriptionResponse


class TranscriberRestController:
    """Implements the transcriber REST controller"""

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
            response_model=TranscriptionResponse
        )
        async def transcribe(
            file: UploadFile = File(...)
        ) -> TranscriptionResponse:
            """
            Upload an audio/video file and transcribe it.
            
            Args:
                file: Audio/video file to transcribe
                
            Returns:
                Transcription response containing paths to generated files
            """
            try:
                # Ensure directories exist before processing
                self._ensure_directories()
                
                # Save the uploaded file
                input_file_path = self.input_directory / file.filename
                with input_file_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                logger.info("Audio file saved for transcription", 
                          extra={
                              "input_path": str(input_file_path),
                              "original_name": file.filename
                          })

                # Transcribe the file with fixed parameters
                text_file_path, subtitle_file_path = self.transcriber_service_manager.transcribe_file(
                    input_file=input_file_path,
                    output_directory=self.output_directory,
                    beam_size=5,  # Fixed default value
                    use_vad=True  # Fixed default value
                )

                # Get language detection info from the last transcription
                detected_language = "unknown"  # TODO: Get from transcriber
                language_confidence = 0.0      # TODO: Get from transcriber

                return TranscriptionResponse(
                    message="File transcribed successfully",
                    text_file_path=str(text_file_path),
                    subtitle_file_path=str(subtitle_file_path),
                    detected_language=detected_language,
                    language_confidence=language_confidence
                )

            except Exception as error:
                logger.error("Transcription failed", exc_info=error)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(error)
                )
