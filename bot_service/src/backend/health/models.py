from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Represents the health response"""

    alive: bool
