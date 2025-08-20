import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

from faster_whisper import WhisperModel
from sqlalchemy.orm import Session

from common.logger import get_logger
from common.configuration import Configuration
from common.data_model import TranscriberConfiguration
from database.manager import DatabaseServiceManager
from transcriber.db_models import TranscriptionJob

logger = get_logger(__name__)

def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds_part:02},{milliseconds:03}"

class TranscriberManager:
    """Manages transcription jobs and Faster-Whisper model"""

    # Required files that must exist in a valid CTranslate2 model directory
    REQUIRED_MODEL_FILES = {"model.bin", "config.json", "tokenizer.json"}

    def __init__(self, config: Configuration):
        """Initialize transcription manager"""
        self.config = config.configuration()
        self.transcriber_config = self.config.transcriber_configuration
        self.db_manager = DatabaseServiceManager(config)
        self.db_session = self.db_manager.postgres_db_service().get_db_session()
        
        # Initialize model
        self._initialize_model()

    def create_job(self, file_path: str, output_formats: List[str] = ["txt", "srt"]) -> str:
        """Create a new transcription job in the database"""
        job_id = str(uuid4())
        
        job = TranscriptionJob(
            id=job_id,
            status="pending",
            processed_file_path=file_path,
            output_file_path=str(Path(file_path).parent / "output")
        )
        
        try:
            self.db_session.add(job)
            self.db_session.commit()
            logger.info(f"Created transcription job {job_id}")
            return job_id
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create job: {str(e)}")
            raise

    def update_job_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Update job status in database"""
        try:
            job = self.db_session.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                self.db_session.commit()
                logger.info(f"Updated job {job_id} status to {status}")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update job status: {str(e)}")
            raise

    def process_file(self, file_path: str, job_id: str, output_formats: List[str] = ["txt", "srt"]) -> None:
        """Process a transcription job"""
        try:
            # Update job status to processing
            self.update_job_status(job_id, "processing")
            
            # Get job from database
            job = self.db_session.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Create output directory
            output_dir = Path(job.output_file_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Run transcription
            segments, info = self.model.transcribe(
                str(file_path),
                beam_size=5,
                vad_filter=True
            )
            
            # Generate outputs
            output_files = {}
            
            if "txt" in output_formats:
                txt_path = output_dir / f"{Path(file_path).stem}.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    for segment in segments:
                        f.write(f"{segment.text.strip()}\n")
                output_files["txt"] = str(txt_path)
            
            if "srt" in output_formats:
                srt_path = output_dir / f"{Path(file_path).stem}.srt"
                with open(srt_path, "w", encoding="utf-8") as f:
                    for i, segment in enumerate(segments, 1):
                        f.write(f"{i}\n")
                        f.write(f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n")
                        f.write(f"{segment.text.strip()}\n\n")
                output_files["srt"] = str(srt_path)
            
            # Update job with output paths
            job.output_file_path = str(output_files.get("srt", output_files.get("txt")))
            job.status = "completed"
            self.db_session.commit()
            
            logger.info(f"Successfully processed job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to process job {job_id}: {str(e)}")
            self.update_job_status(job_id, "failed", str(e))
            raise

    def _initialize_model(self) -> None:
        """Initialize the Whisper model"""
        try:
            # Set up model paths
            workspace_root = Path(os.getcwd()).resolve()
            etc_directory = workspace_root / "etc"
            models_directory = Path(self.transcriber_config.models_directory or (etc_directory / "models")).resolve()
            model_instance_directory = (models_directory / self.transcriber_config.model_name).resolve()
            
            # Create directories
            etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            models_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
            
            # Find or download model
            model_dir = self._find_model_directory(model_instance_directory)
            if not model_dir:
                logger.info("Downloading model...")
                self._download_model(self.transcriber_config.model_name, model_instance_directory)
                model_dir = self._find_model_directory(model_instance_directory)
                if not model_dir:
                    raise RuntimeError("Model not found after download")
            
            # Load model
            logger.info("Loading model...")
            self.model = WhisperModel(
                str(model_dir),
                device=self.transcriber_config.device,
                compute_type=self.transcriber_config.compute_type
            )
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise

    def _download_model(self, model_name: str, download_directory: Path) -> None:
        """Download model files"""
        download_directory.mkdir(parents=True, exist_ok=True)
        _ = WhisperModel(
            model_name,
            device=self.transcriber_config.device,
            compute_type=self.transcriber_config.compute_type,
            download_root=str(download_directory)
        )

    def _find_model_directory(self, preferred_directory: Path) -> Optional[Path]:
        """Find directory containing model files"""
        # Direct path
        if self._is_valid_model_directory(preferred_directory):
            return preferred_directory

        # Nested directories
        for model_file_path in preferred_directory.glob("**/model.bin"):
            if self._is_valid_model_directory(model_file_path.parent):
                return model_file_path.parent

        # HuggingFace cache structure
        root_directory = preferred_directory.parent
        model_name_hint = preferred_directory.name
        candidates = []

        # Model-specific snapshots
        for path in root_directory.glob(f"models--*{model_name_hint}*/snapshots/*/model.bin"):
            if self._is_valid_model_directory(path.parent):
                candidates.append(path.parent)

        # All snapshots as fallback
        if not candidates:
            for path in root_directory.glob("models--*/snapshots/*/model.bin"):
                if self._is_valid_model_directory(path.parent):
                    candidates.append(path.parent)

        if candidates:
            return sorted(candidates, key=lambda d: d.stat().st_mtime, reverse=True)[0]

        return None

    def _is_valid_model_directory(self, directory_path: Path) -> bool:
        """Check if directory contains required model files"""
        return directory_path.is_dir() and all(
            (directory_path / file).exists() for file in self.REQUIRED_MODEL_FILES
        )
