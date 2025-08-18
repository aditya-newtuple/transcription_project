"""Contains the user API response models."""

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Represents the user API Request"""

    id: int
    username: str
    email: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
