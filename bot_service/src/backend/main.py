# Application startup
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

from argparse import ArgumentParser

import uvicorn
from auth.manager import AuthManager
from common.configuration import Configuration
from common.logger import _logger_instance, logger
from database.manager import DatabaseServiceManager
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from health.controller import HealthRestController
from health.manager import HealthServiceManager
from LLM.manager import LLMServiceManager
from metrics.controller import MetricsRestController
from metrics.manager import MetricsService
from transcriber.controller import TranscriberRestController
from transcriber.manager import TranscriberServiceManager
from jobs.manager import JobManager
from jobs.db_models import JobModelService
from jobs.controller import JobsRestController
from user.controller import UserRestController
from user.db_models import UserModelService
from user.manager import UserServiceManager
from files.db_models import FileModelService
from transcripts.db_models import TranscriptModelService
from common.redis import RedisManager
from files.manager import FileManager
from files.controller import FilesRestController
from transcripts.manager import TranscriptManager
from transcripts.controller import TranscriptsRestController

parser = ArgumentParser(description="Runs the BOT service")
parser.add_argument("-e", "--env", help="Path to .env file", default="./etc/.env")
args = parser.parse_args()
load_dotenv(args.env)

# common services

# logger = Logger()
logger.info("Starting BOT service...")
# _logger_instance.enable_otel()

config = Configuration()
config_env = config.configuration()
config_ini = config.config_ini()
app_router = APIRouter()


auth_manager = AuthManager(config)
health_service_manager = HealthServiceManager()
health_rest_contoller = HealthRestController(health_service_manager).prepare(app_router)

# task_service = TasksService()
# task_rest_controller = TaskRestController(task_service).prepare(app_router)

database_service_manager = DatabaseServiceManager(config)
llm_service_manager = LLMServiceManager()

# Initialize transcriber service with configuration from environment
transcriber_service_manager = TranscriberServiceManager(config_env.transcriber_configuration)

# --- Define a dependency that returns the singleton ---
def get_transcriber() -> TranscriberServiceManager:
    return transcriber_service_manager

user_db_model_service = UserModelService(database_service_manager)
user_service_manager = UserServiceManager(user_db_model_service, config)
user_rest_controller = UserRestController(user_service_manager, database_service_manager)
user_rest_controller.prepare(app_router)

transcriber_rest_controller = TranscriberRestController(
    transcriber_manager=transcriber_service_manager,                 
    get_transcriber_dep=get_transcriber,     
)
transcriber_rest_controller.prepare(app_router)

#Files service
file_model_service = FileModelService(database_service_manager)

# Transcript service
transcript_model_service = TranscriptModelService(database_service_manager)

# Initialize Redis manager
redis_manager = RedisManager(config)

# Jobs service
job_model_service = JobModelService(database_service_manager)
job_manager = JobManager(job_model_service, file_model_service, transcriber_service_manager, transcript_model_service, redis_manager)
jobs_rest_controller = JobsRestController(
    job_manager,
    file_model_service,
    transcriber_service_manager,
    transcript_model_service,
    redis_manager
)
jobs_rest_controller.prepare(app_router)

# Files service
file_manager = FileManager(file_model_service, job_manager)
files_rest_controller = FilesRestController(file_manager, config)
files_rest_controller.prepare(app_router)

# Transcripts service
transcript_manager = TranscriptManager(transcript_model_service)
transcripts_rest_controller = TranscriptsRestController(transcript_manager)
transcripts_rest_controller.prepare(app_router)

# Metrics service
metrics_service_manager = MetricsService()
metrics_rest_controller = MetricsRestController(metrics_service_manager).prepare(app_router, Depends(user_rest_controller.get_current_username))


app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
# app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(app_router, prefix="/v1/api")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",                       # keep original style
        host=config_env.server_configuration.host,
        port=int(config_env.server_configuration.port),
        timeout_keep_alive=7200,
        reload=False,                     # ensure no reloader in Docker
        log_level="info",
    )