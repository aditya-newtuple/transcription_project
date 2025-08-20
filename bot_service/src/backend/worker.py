"""Background worker for processing transcription jobs"""

import signal
import sys
import time
from typing import Optional

from pathlib import Path
from common.configuration import Configuration
from common.logger import get_logger
from common.redis import RedisManager
from database.manager import DatabaseServiceManager
from files.db_models import FileModelService, FileStatus
from jobs.db_models import JobModelService
from transcriber.manager import TranscriberManager
from transcripts.db_models import TranscriptModelService
from transcripts.models.request import CreateTranscriptRequest
from common.models import TranscriptFormat

logger = get_logger(__name__)

class TranscriptionWorker:
    """Worker that processes transcription jobs from Redis queue"""

    def __init__(self):
        """Initialize worker"""
        config = Configuration()
        self.config = config.configuration()
        
        self.redis_manager = RedisManager(config)
        
        database_service_manager = DatabaseServiceManager(config)
        self.job_model_service = JobModelService(database_service_manager)
        self.file_model_service = FileModelService(database_service_manager)
        self.transcript_model_service = TranscriptModelService(database_service_manager)
        
        self.transcriber_manager = TranscriberManager(self.config.transcriber_configuration)
        
        # Define and create output directory
        workspace_root = Path.cwd().resolve()
        self.output_directory = workspace_root / "etc" / "output"
        self.output_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
        self.should_exit = False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum: int, frame: Optional[object]) -> None:
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal, stopping worker...")
        self.should_exit = True

    def process_job(self, job_data: dict) -> None:
        """Process a single transcription job"""
        job_id = job_data.get("job_id")
        file_id = job_data.get("file_id")

        if not job_id or not file_id:
            logger.error("Invalid job data received", extra={"job_data": job_data})
            return

        try:
            # Get file details from the database
            db_file = self.file_model_service.get_file(file_id)
            if not db_file:
                raise RuntimeError(f"File with ID {file_id} not found in the database.")
            
            logger.info(f"Processing file {db_file.source_name} for job {job_id}")
            
            # Update file status to RUNNING
            self.file_model_service.update_file_status(file_id, FileStatus.RUNNING)
            self.job_model_service.update_job_counts(job_id)

            # Transcribe the file
            input_file_path = Path(db_file.source_path)
            text_path, srt_path, _ = self.transcriber_manager.transcribe_file(
                input_file=input_file_path,
                output_directory=self.output_directory
            )

            # Read the output files and create transcript records
            with text_path.open("r", encoding="utf-8") as f:
                text_content = f.read()
            
            with srt_path.open("r", encoding="utf-8") as f:
                srt_content = f.read()

            # Create transcript records in the database
            # TODO: Replace hardcoded user ID with actual user from auth
            self.transcript_model_service.create_transcript(
                CreateTranscriptRequest(
                    file_id=file_id,
                    format=TranscriptFormat.TXT,
                    content=text_content
                ),
                created_by=1
            )
            self.transcript_model_service.create_transcript(
                CreateTranscriptRequest(
                    file_id=file_id,
                    format=TranscriptFormat.SRT,
                    content=srt_content
                ),
                created_by=1
            )
            
            # Update file status to SUCCEEDED
            self.file_model_service.update_file_status(file_id, FileStatus.SUCCEEDED)
            logger.info(f"Successfully processed file {db_file.source_name} for job {job_id}")

        except Exception as e:
            logger.error(f"Failed to process file {file_id} for job {job_id}", exc_info=e)
            # Update file status to FAILED
            self.file_model_service.update_file_status(file_id, FileStatus.FAILED, str(e))
        
        finally:
            # Always update the main job status
            self.job_model_service.update_job_counts(job_id)

    def run(self) -> None:
        """Main worker loop"""
        logger.info("Starting transcription worker...")
        
        while not self.should_exit:
            try:
                # Get next job from queue
                job_data = self.redis_manager.dequeue_job()
                
                if job_data:
                    self.process_job(job_data)
                else:
                    # No jobs available, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                time.sleep(5)  # Back off on error
                
        logger.info("Worker shutdown complete")

def main():
    """Main entry point"""
    worker = TranscriptionWorker()
    worker.run()

if __name__ == "__main__":
    main()
