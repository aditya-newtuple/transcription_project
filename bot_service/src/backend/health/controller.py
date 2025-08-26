"""Health REST controller module"""

# from common.controller import APIRouter
from fastapi import APIRouter, Request
from health.manager import HealthServiceManager
from health.models import HealthResponse
import shutil

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

        @app.get("/disk-space")
        async def get_disk_space():
            """Returns disk space information"""
                
            # Get disk usage statistics
            total, used, free = shutil.disk_usage("/")
            percentage = (used / total) * 100
            
            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "percentage": round(percentage, 1),
                "status": "healthy" if percentage < 60 else "warning" if percentage < 80 else "critical"
            }
