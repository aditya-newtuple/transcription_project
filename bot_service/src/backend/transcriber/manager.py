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
    
    # Singleton instance
    _instance = None

    def __new__(cls, config: Optional[TranscriberConfiguration] = None):
        if cls._instance is None:
            if config is None:
                raise ValueError("Configuration is required for first initialization")
            cls._instance = super(TranscriberServiceManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[TranscriberConfiguration] = None):
        """
        Initialize the transcription service manager.
        
        Args:
            config: Configuration for the transcriber service from environment
        """
        # Skip initialization if already done
        if hasattr(self, '_initialized') and self._initialized:
            return

        if config is None:
            raise ValueError("Configuration is required for first initialization")

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
        self._initialized = True

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
    ) -> Tuple[Path, Path, object]:
        """
        Transcribe an audio/video file and generate .txt and .srt outputs.
        
        Args:
            input_file: Path to input audio/video file
            output_directory: Directory to save output files
            beam_size: Beam size for decoding (default: 5)
            use_vad: Whether to use voice activity detection (default: True)
            
        Returns:
            Tuple of (text_file_path, subtitle_file_path, transcription_info)
        """
        if not hasattr(self, "model") or self.model is None:
            raise RuntimeError("Model not initialized")

        # Convert to Path objects if they're strings
        input_file = Path(input_file)
        output_directory = Path(output_directory)

        # Verify input file
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        if not input_file.is_file():
            raise ValueError(f"Input path is not a file: {input_file}")

        logger.info("Starting transcription", extra={"input_file": str(input_file.absolute())})
        
        try:
            # Run transcription with more detailed logging
            logger.info("Running Whisper model transcription")
            segments_generator = self.model.transcribe(
                str(input_file.absolute()),
                vad_filter=use_vad,
                beam_size=beam_size
            )
            
            # Convert generator to list and check content
            segments = list(segments_generator[0])  # [0] contains segments, [1] contains info
            transcription_info = segments_generator[1]
            
            if not segments:
                logger.error("Transcription produced no segments")
                raise ValueError("Transcription produced no segments. The audio file might be empty or contain no speech.")

            # Prepare output paths
            output_directory.mkdir(parents=True, exist_ok=True)
            text_file_path = output_directory / f"{input_file.stem}.txt"
            subtitle_file_path = output_directory / f"{input_file.stem}.srt"

            # Write outputs with validation
            valid_segments = []
            for segment in segments:
                if segment.text and segment.text.strip():
                    valid_segments.append(segment)

            if not valid_segments:
                logger.error("No valid text segments found in transcription")
                raise ValueError("Transcription produced no valid text segments. The audio might contain no recognizable speech.")

            logger.info(f"Writing transcripts with {len(valid_segments)} valid segments")

            # Write text file
            with text_file_path.open("w", encoding="utf-8") as text_file:
                for segment in valid_segments:
                    text_file.write(segment.text.strip() + "\n")

            # Write SRT file
            with subtitle_file_path.open("w", encoding="utf-8") as subtitle_file:
                for idx, segment in enumerate(valid_segments, 1):
                    subtitle_file.write(f"{idx}\n")
                    subtitle_file.write(f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n")
                    subtitle_file.write(f"{segment.text.strip()}\n\n")

            # Verify files were created successfully
            if not text_file_path.exists() or text_file_path.stat().st_size == 0:
                raise RuntimeError("Failed to create text transcript file or file is empty")
            if not subtitle_file_path.exists() or subtitle_file_path.stat().st_size == 0:
                raise RuntimeError("Failed to create subtitle file or file is empty")

            logger.info("Transcription completed successfully", 
                       extra={
                           "text_file": str(text_file_path),
                           "subtitle_file": str(subtitle_file_path),
                           "valid_segments": len(valid_segments),
                           "total_segments": len(segments)
                       })

            return text_file_path, subtitle_file_path, transcription_info

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Clean up any partial output files
            for file_path in [text_file_path, subtitle_file_path]:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up file {file_path}: {cleanup_error}")
            
            raise RuntimeError(error_msg)

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