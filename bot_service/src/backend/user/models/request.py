from pydantic import BaseModel as PydanticBaseModel


class UserCreateRequest(PydanticBaseModel):
    """Represents the user API Request"""

    email: str
    username: str
    password: str
