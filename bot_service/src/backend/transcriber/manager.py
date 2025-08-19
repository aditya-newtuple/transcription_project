import os
from pathlib import Path
from typing import Optional, List, Tuple
from faster_whisper import WhisperModel
from common.logger import logger
from common.data_model import TranscriberConfiguration


def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds_part:02},{milliseconds:03}"


class TranscriberServiceManager:
    """
    Manages the Faster-Whisper transcription service with automatic model handling:
    
    - Automatically downloads the model if not present
    - Uses existing model if already downloaded
    - Supports CPU and GPU inference
    - Generates both .txt and .srt outputs
    """

    # Required files that must exist in a valid CTranslate2 model directory
    REQUIRED_MODEL_FILES = {"model.bin", "config.json", "tokenizer.json"}

    def __init__(self, config: TranscriberConfiguration) -> None:
        """
        Initialize the transcription service manager.
        
        Args:
            config: Configuration for the transcriber service from environment
        """
        self.config = config
        
        # Resolve models directory path
        workspace_root = Path(os.getcwd()).resolve()
        etc_directory = workspace_root / "etc"
        self.models_directory = Path(config.models_directory or (etc_directory / "models")).resolve()
        self.model_instance_directory = (self.models_directory / config.model_name).resolve()

        # Create etc directory if it doesn't exist
        etc_directory.mkdir(mode=0o755, parents=True, exist_ok=True)

        logger.info("Initializing TranscriberServiceManager", 
                   extra={
                       "model_name": config.model_name,
                       "device": config.device,
                       "compute_type": config.compute_type,
                       "models_directory": str(self.models_directory)
                   })

        # Ensure model is available and loaded
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the model, downloading if necessary."""
        # Try to find existing model
        model_directory = self._find_model_directory(self.model_instance_directory)

        if model_directory is None:
            logger.info("No local model found, initiating download", 
                       extra={"model_path": str(self.model_instance_directory)})
            
            # Allow online download
            self._set_offline_mode(False)
            
            try:
                self._download_model(self.config.model_name, self.model_instance_directory)
                logger.info("Model downloaded successfully")
                
                # Verify downloaded model
                model_directory = self._find_model_directory(self.model_instance_directory)
                if model_directory is None:
                    raise RuntimeError("Model files not found after download")
                    
            except Exception as error:
                logger.error("Failed to download model", exc_info=error)
                raise RuntimeError(f"Failed to download model: {error}")
            
            finally:
                # Return to offline mode
                self._set_offline_mode(True)
        else:
            logger.info("Using existing model", extra={"model_path": str(model_directory)})

        # Load the model
        try:
            logger.info("Loading model", extra={"device": self.config.device, "compute_type": self.config.compute_type})
            self.model = WhisperModel(
                str(model_directory),
                device=self.config.device,
                compute_type=self.config.compute_type
            )
            logger.info("Model loaded successfully")
            
        except Exception as error:
            logger.error("Failed to load model", exc_info=error)
            raise RuntimeError(f"Failed to load model: {error}")

    def transcribe_file(
        self,
        input_file: Path,
        output_directory: Path,
        beam_size: int = 5,
        use_vad: bool = True
    ) -> Tuple[Path, Path]:
        """
        Transcribe an audio/video file and generate .txt and .srt outputs.
        
        Args:
            input_file: Path to input audio/video file
            output_directory: Directory to save output files
            beam_size: Beam size for decoding (default: 5)
            use_vad: Whether to use voice activity detection (default: True)
            
        Returns:
            Tuple of (text_file_path, subtitle_file_path) for the generated output files
        """
        if not hasattr(self, "model") or self.model is None:
            raise RuntimeError("Model not initialized")

        logger.info("Starting transcription", extra={"input_file": input_file.name})
        
        # Run transcription
        transcript_segments, transcription_info = self.model.transcribe(
            str(input_file),
            vad_filter=use_vad,
            beam_size=beam_size
        )
        
        logger.info("Transcription completed", 
                   extra={
                       "detected_language": transcription_info.language,
                       "language_confidence": transcription_info.language_probability
                   })

        # Prepare output paths
        output_directory.mkdir(parents=True, exist_ok=True)
        text_file_path = output_directory / f"{input_file.stem}.txt"
        subtitle_file_path = output_directory / f"{input_file.stem}.srt"

        # Write outputs
        with text_file_path.open("w", encoding="utf-8") as text_file, \
             subtitle_file_path.open("w", encoding="utf-8") as subtitle_file:
            
            for segment_index, segment in enumerate(transcript_segments, 1):
                transcript_text = segment.text.strip()
                
                # Write plain text
                text_file.write(transcript_text + "\n")
                
                # Write SRT entry
                subtitle_file.write(f"{segment_index}\n")
                subtitle_file.write(f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n")
                subtitle_file.write(f"{transcript_text}\n\n")

        logger.info("Generated output files", 
                   extra={
                       "text_file": text_file_path.name,
                       "subtitle_file": subtitle_file_path.name
                   })
        
        return text_file_path, subtitle_file_path

    def _download_model(self, model_name: str, download_directory: Path) -> None:
        """Download model files to the specified directory."""
        download_directory.mkdir(parents=True, exist_ok=True)
        _ = WhisperModel(
            model_name,
            device=self.config.device,
            compute_type=self.config.compute_type,
            download_root=str(download_directory)
        )

    def _set_offline_mode(self, offline: bool) -> None:
        """Toggle offline mode for Hugging Face Hub."""
        if offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)

    def _is_valid_model_directory(self, directory_path: Path) -> bool:
        """Check if directory contains all required model files."""
        return directory_path.is_dir() and all((directory_path / file).exists() for file in self.REQUIRED_MODEL_FILES)

    def _find_model_directory(self, preferred_directory: Path) -> Optional[Path]:
        """
        Find directory containing model files, checking:
        1. Direct path
        2. Nested directories
        3. HuggingFace cache structure
        """
        # Check if preferred_directory itself contains the model
        if self._is_valid_model_directory(preferred_directory):
            return preferred_directory

        # Check nested directories
        for model_file_path in preferred_directory.glob("**/model.bin"):
            if self._is_valid_model_directory(model_file_path.parent):
                return model_file_path.parent

        # Check HuggingFace cache structure
        root_directory = preferred_directory.parent
        model_name_hint = preferred_directory.name
        candidate_directories: List[Path] = []

        # Check model-specific snapshots
        for model_file_path in root_directory.glob(f"models--*{model_name_hint}*/snapshots/*/model.bin"):
            if self._is_valid_model_directory(model_file_path.parent):
                candidate_directories.append(model_file_path.parent)

        # Check all snapshots as fallback
        if not candidate_directories:
            for model_file_path in root_directory.glob("models--*/snapshots/*/model.bin"):
                if self._is_valid_model_directory(model_file_path.parent):
                    candidate_directories.append(model_file_path.parent)

        if candidate_directories:
            # Return most recently modified
            return sorted(candidate_directories, key=lambda d: d.stat().st_mtime, reverse=True)[0]

        return None
