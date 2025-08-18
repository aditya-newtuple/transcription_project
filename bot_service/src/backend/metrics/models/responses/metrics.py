# from common.data_model import BaseModel

# NOTE: Overriding to use pydantic v2 with latest fastapi
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model for all data models"""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
    )


class MetricResponse(BaseModel):
    """Represents the health response"""

    alive: bool
