"""Health REST controller module"""

import secrets
from typing import Annotated

from auth.manager import basic_security
from common.logger import logger, tracer
from common.utils import verify_password
from database.manager import DatabaseServiceManager
from exceptions.db import DBException
from exceptions.user import InactiveUser, UserExists
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBasicCredentials
from monitoring.prometheus import OPERATION_TIME, REQUEST_COUNT
from user.manager import UserServiceManager
from user.models.interface import User
from user.models.request import UserCreateRequest
from user.models.response import UserResponse


class UserRestController:
    """Implements health REST controller"""

    def __init__(self, user_service_manager: UserServiceManager, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.user_service_manager = user_service_manager
        self.current_db = database_service_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

    async def get_current_username(
        self,
        credentials: Annotated[HTTPBasicCredentials, Depends(basic_security)],
    ):
        """Get the current username from the credentials."""
        current_username_bytes = credentials.username.encode("utf8")
        current_password_bytes = credentials.password.encode("utf8")

        is_correct_username, is_correct_password = False, False

        try:
            db_user = self.user_service_manager.get_active_user(username=credentials.username)
        except InactiveUser as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
                # headers={"WWW-Authenticate": "Basic"},
            )

        if db_user:
            correct_username_bytes = bytes(str(db_user.username), encoding="utf8")
            correct_password_bytes = bytes(str(db_user.hashed_password), encoding="utf8")

            is_correct_password = verify_password(current_password_bytes, correct_password_bytes)
            is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)

            if not is_correct_username or not is_correct_password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect credentials",
                    # headers={"WWW-Authenticate": "Basic"},
                )
            return db_user  # noqa

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username does not exist or is inactive",
            # headers={"WWW-Authenticate": "Basic"},
        )

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the user REST controller.
        """

        @app.post("/create_user", status_code=status.HTTP_200_OK, tags=["users"], response_model=UserResponse)
        async def create_user(request: Request, user_create_request: UserCreateRequest = Depends()):  # noqa: F841, ASYNC124
            """
            Create a new user.
            """
            try:
                with OPERATION_TIME.labels(request.url.path, "api").time():
                    user = self.user_service_manager.add_user(user_create_request)
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                    return user  # noqa: ASYNC910

            except (UserExists, DBException) as e:
                REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

            except BaseException as e:
                logger.exception(f"Could not create user due to {e}")
                REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get(
            "/user",
            status_code=status.HTTP_200_OK,
            tags=["users"],
            response_model=UserResponse,
        )
        async def get_user(request: Request, user: Annotated[User, Depends(self.get_current_username)]):  # noqa: ASYNC124
            """
            Get user details.
            """
            with tracer.start_as_current_span(f"UserRestController.get_user.{user.username}"):
                logger.info(f"Fetching user details for {user.username}", extra={"username": user.username})

                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        db_user = self.user_service_manager.get_user(username=user.username)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return db_user  # noqa: ASYNC910

                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except Exception as e:
                    logger.exception(f"Could not fetch user details due to {e}", extra={"username": user.username})
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get(
            "/delete_user",
            status_code=status.HTTP_200_OK,
            tags=["users"],
            response_model=UserResponse,
        )
        async def delete_user(request: Request, username: str, auth_username: Annotated[str, Depends(self.get_current_username)]):  # noqa: F841, ASYNC124
            """
            Delete a user.
            """
            try:

                with OPERATION_TIME.labels(request.url.path, "api").time():
                    db_user = self.user_service_manager.delete_user(username=username)
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                    return db_user  # noqa: ASYNC910

            except (InactiveUser, DBException) as e:
                REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

            except Exception as e:
                REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
