from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class User(PydanticBaseModel):
    id: int
    email: str
    username: str
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(PydanticBaseModel):
    email: str
    username: str
    password: str

    model_config = ConfigDict(
        from_attributes=True,
    )
