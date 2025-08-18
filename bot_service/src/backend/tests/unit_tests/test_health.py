import pytest
from health.manager import HealthServiceManager

health_manager = HealthServiceManager()


@pytest.mark.asyncio
async def test_health_ping():
    health_response = await health_manager.ping()
    assert isinstance(health_response.model_dump(), dict)


# pytest - v tests/
