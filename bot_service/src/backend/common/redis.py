"""Redis connection manager"""

import json
from typing import Any, Optional

import redis
from common.configuration import Configuration
from common.logger import get_logger

logger = get_logger(__name__)

class RedisManager:
    """Redis connection manager"""

    def __init__(self, config: Configuration):
        """Initialize Redis connection"""
        self.config = config.configuration()
        self.redis_config = self.config.redis_configuration
        self.redis_client = redis.Redis(
            host=self.redis_config.host,
            port=self.redis_config.port,
            db=self.redis_config.db,
            password=self.redis_config.password,
            decode_responses=True
        )
        self.queue_name = self.redis_config.queue_name
        
        # Disable persistence to avoid disk write issues
        try:
            self.redis_client.config_set('save', '')
            self.redis_client.config_set('appendonly', 'no')
            logger.info("Redis persistence disabled")
        except Exception as e:
            logger.warning(f"Could not disable Redis persistence: {str(e)}")

    def enqueue_job(self, job_data: dict[str, Any]) -> str:
        """
        Add a job to the Redis queue
        Returns the job ID
        """
        try:
            job_id = job_data.get("job_id")
            self.redis_client.rpush(self.queue_name, json.dumps(job_data))
            logger.info(f"Enqueued job {job_id} to Redis queue")
            return job_id
        except Exception as e:
            logger.error(f"Failed to enqueue job to Redis: {str(e)}")
            raise

    def dequeue_job(self) -> Optional[dict[str, Any]]:
        """
        Get the next job from the Redis queue
        Returns None if queue is empty
        """
        try:
            # BLPOP blocks until a job is available
            result = self.redis_client.blpop(self.queue_name, timeout=1)
            if result:
                _, job_json = result
                job_data = json.loads(job_json)
                logger.info(f"Dequeued job {job_data.get('job_id')} from Redis queue")
                return job_data
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue job from Redis: {str(e)}")
            raise

    def get_queue_length(self) -> int:
        """Get number of jobs in queue"""
        return self.redis_client.llen(self.queue_name)

# Initialize Redis manager
# redis_manager = RedisManager(Configuration())
