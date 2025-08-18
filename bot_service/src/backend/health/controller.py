"""Health REST controller module"""

# from common.controller import APIRouter
from fastapi import APIRouter, Request
from health.manager import HealthServiceManager
from health.models import HealthResponse


class HealthRestController:
    """Implements health REST controller"""

    def __init__(self, health_service_manager: HealthServiceManager) -> None:
        super().__init__()
        self._health_service_manager = health_service_manager

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the health REST controller.
        """

        @app.post("/health", response_model=HealthResponse)
        async def health(request: Request) -> HealthResponse:
            """Returns the health response"""
            print("Health check request received")
            response = await request.body()
            print(f"Request body: {response.decode()}")
            return await self._health_service_manager.ping()
