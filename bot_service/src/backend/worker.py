"""Background worker for processing transcription jobs"""

import signal
import sys
import time
from typing import Optional

from common.configuration import Configuration
from common.logger import get_logger
from common.redis import RedisManager
from transcriber.manager import TranscriberManager

logger = get_logger(__name__)

class TranscriptionWorker:
    """Worker that processes transcription jobs from Redis queue"""

    def __init__(self):
        """Initialize worker"""
        self.config = Configuration()
        self.redis_manager = RedisManager(self.config)
        self.transcriber_manager = TranscriberManager(self.config)
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
        try:
            job_id = job_data.get("job_id")
            file_path = job_data.get("file_path")
            output_formats = job_data.get("output_formats", ["txt"])
            
            logger.info(f"Processing job {job_id} for file {file_path}")
            
            # Call transcriber manager to process the file
            self.transcriber_manager.process_file(
                file_path=file_path,
                job_id=job_id,
                output_formats=output_formats
            )
            
            logger.info(f"Successfully processed job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to process job {job_id}: {str(e)}")
            # Update job status to failed in database
            self.transcriber_manager.update_job_status(job_id, "failed", str(e))

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
