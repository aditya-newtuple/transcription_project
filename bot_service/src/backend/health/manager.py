from common.logger import logger, tracer
from health.models import HealthResponse


class HealthServiceManager:
    """Implements the health service manager"""

    async def ping(self) -> HealthResponse:
        """Returns the health response"""
        with tracer.start_as_current_span("HealthServiceManager.ping"):
            logger.info("HealthServiceManager.ping")
            return HealthResponse(alive=True)  # noqa
