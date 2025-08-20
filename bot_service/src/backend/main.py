# Application startup
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from argparse import ArgumentParser

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

from common.configuration import Configuration
from common.logger import get_logger
from health.controller import HealthRestController
from health.manager import HealthServiceManager
from metrics.controller import MetricsRestController
from metrics.manager import MetricsService
from user.controller import UserRestController
from user.manager import UserServiceManager
from user.db_models import UserModelService
from database.manager import DatabaseServiceManager
from auth.manager import AuthManager
from transcriber.manager import TranscriberServiceManager

from transcriber.controller import TranscriberRestController
from jobs.controller import JobsRestController
from jobs.manager import JobManager
from jobs.db_models import JobModelService
from files.controller import FilesRestController
from files.manager import FileManager
from files.db_models import FileModelService
from transcripts.controller import TranscriptsRestController
from transcripts.manager import TranscriptManager
from transcripts.db_models import TranscriptModelService

logger = get_logger(__name__)

# Parse arguments
parser = ArgumentParser(description="Runs the transcription service")
parser.add_argument("-e", "--env", help="Path to .env file", default="./etc/.env")
args = parser.parse_args()
load_dotenv(args.env)

# Initialize configuration
logger.info("Starting transcription service...")
config = Configuration()
config_env = config.configuration()

# Initialize database and services
database_service_manager = DatabaseServiceManager(config)

# Initialize controllers
app_router = APIRouter()

# Health check
health_service_manager = HealthServiceManager()
health_rest_controller = HealthRestController(health_service_manager)
health_rest_controller.prepare(app_router)

# User management
auth_manager = AuthManager(config)
user_db_model_service = UserModelService(database_service_manager)
user_service_manager = UserServiceManager(user_db_model_service, config)
user_rest_controller = UserRestController(user_service_manager, database_service_manager)
user_rest_controller.prepare(app_router)


# Initialize transcriber service with configuration from environment
transcriber_service_manager = TranscriberServiceManager(config_env.transcriber_configuration)
transcriber_rest_controller = TranscriberRestController(transcriber_service_manager)
transcriber_rest_controller.prepare(app_router)


# Jobs service
job_model_service = JobModelService(database_service_manager)
job_manager = JobManager(job_model_service)
jobs_rest_controller = JobsRestController(job_manager)
jobs_rest_controller.prepare(app_router)

# Files service
file_model_service = FileModelService(database_service_manager)
file_manager = FileManager(file_model_service, job_manager)
files_rest_controller = FilesRestController(file_manager, config)
files_rest_controller.prepare(app_router)

# Transcripts service
transcript_model_service = TranscriptModelService(database_service_manager)
transcript_manager = TranscriptManager(transcript_model_service)
transcripts_rest_controller = TranscriptsRestController(transcript_manager)
transcripts_rest_controller.prepare(app_router)

# Metrics
metrics_service_manager = MetricsService()
metrics_rest_controller = MetricsRestController(metrics_service_manager)
metrics_rest_controller.prepare(app_router, Depends(user_rest_controller.get_current_username))

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(app_router, prefix="/v1/api")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config_env.server_configuration.host,
        port=int(config_env.server_configuration.port),
        timeout_keep_alive=600,
        reload=True
    )
