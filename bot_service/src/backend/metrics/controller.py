"""Health REST controller module"""

# from common.controller import APIRouter
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from metrics.manager import MetricsService
from prometheus_client import CONTENT_TYPE_LATEST


class MetricsRestController:
    """Implements health REST controller"""

    def __init__(self, metrics_service_manager: MetricsService) -> None:
        super().__init__()
        self.metrics_service_manager = metrics_service_manager

    def prepare(self, app: APIRouter, security: Depends) -> None:

        @app.get("/metrics", dependencies=[security])
        def all_metrics():
            metrics = self.metrics_service_manager.get_metrics()
            return Response("\n".join(metrics), headers={"Content-Type": CONTENT_TYPE_LATEST})  # noqa: ASYNC910
