"""Worker script to process queued transcription jobs"""

import time
import traceback
from pathlib import Path

from common.configuration import Configuration
from common.logger import logger
from common.redis import RedisManager
from database.manager import DatabaseServiceManager
from files.db_models import FileModelService
from jobs.db_models import JobModelService
from jobs.manager import JobManager
from transcriber.manager import TranscriberServiceManager
from transcripts.db_models import TranscriptModelService
from common.models import JobStatus, FileStatus


def main():
    """Main worker function"""
    try:
        # Initialize services
        config = Configuration()
        database_manager = DatabaseServiceManager(config)
        redis_manager = RedisManager(config)
        
        # Initialize all required services
        job_model_service = JobModelService(database_manager)
        file_model_service = FileModelService(database_manager)
        transcript_model_service = TranscriptModelService(database_manager)
        transcriber_service = TranscriberServiceManager(config.configuration().transcriber_configuration)
        
        # Initialize job manager
        job_manager = JobManager(
            job_model_service=job_model_service,
            file_model_service=file_model_service,
            transcriber_service=transcriber_service,
            transcript_model_service=transcript_model_service,
            redis_manager=redis_manager
        )
        
        logger.info("Worker started, waiting for jobs...")
        
        while True:
            current_file_id = None
            current_job_id = None
            try:
                # Get next job from queue
                job_data = redis_manager.dequeue_job()
                
                if job_data and job_data.get("action") == "transcribe":
                    file_id = job_data.get("file_id")
                    created_by = job_data.get("created_by")
                    source_path = job_data.get("source_path")
                    
                    current_file_id = file_id
                    
                    logger.info(f"Processing file {file_id} from queue")
                    
                    # Get job ID before processing
                    file = file_model_service.get_file(file_id)
                    if file:
                        current_job_id = file.job_id
                        # Update job status to running
                        job_manager.update_job_status(current_job_id, JobStatus.RUNNING)
                    
                    # Process the file
                    job_manager.process_queued_file(
                        file_id=file_id,
                        created_by=created_by,
                        source_path=source_path
                    )
                    
                    # Update job counts and status
                    if current_job_id:
                        job = job_manager.update_job_counts(current_job_id)
                        # Check if all files are processed
                        if job and job.total_count == job.succeeded_count:
                            job_manager.update_job_status(current_job_id, JobStatus.COMPLETED)
                    
                    logger.info(f"Completed processing file {file_id}")
                    
                else:
                    # No job available, wait a bit
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}\n{traceback.format_exc()}")
                
                # Update file and job status on error
                if current_file_id:
                    try:
                        file_model_service.update_file_status(
                            current_file_id, 
                            FileStatus.FAILED,
                            error_message=str(e)
                        )
                    except Exception as status_error:
                        logger.error(f"Failed to update file status: {str(status_error)}")
                
                if current_job_id:
                    try:
                        job = job_model_service.get_job(current_job_id)
                        if job and job.total_count == job.failed_count:
                            job_manager.update_job_status(current_job_id, JobStatus.FAILED)
                    except Exception as status_error:
                        logger.error(f"Failed to update job status: {str(status_error)}")
                
                # Continue processing next job
                continue
                
    except Exception as e:
        logger.error(f"Worker failed to start: {str(e)}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
