from common.configuration import Configuration
from common.logger import logger, tracer
from common.utils import get_password_hash
from exceptions.user import InactiveUser, UserExists
from user.db_models import User, UserModelService
from user.models.interface import UserCreate


class UserServiceManager:
    """Implements the health service manager"""

    def __init__(
        self,
        user_db_model_service: UserModelService,
        config: Configuration,
    ) -> None:
        """
        Initializes the ETL Orchestrator service for unstructured files.

        Args:
            extractor_manager: Data extractor service manager.
            data_loader_manager: Data loader service manager.
            vectordb_service_manager: VectorDB service manager.
        """
        self.user_db_model_service = user_db_model_service

    def add_user(self, user: UserCreate):
        """
        Adds a user to the database.

        Args:
            user: The user to add to the database.
        """
        db_user = self.user_db_model_service.get_user(username=user.username)
        db_user_email = self.user_db_model_service.get_user_by_email(email=user.email)

        if db_user and db_user.is_active or db_user_email and db_user_email.is_active:
            raise UserExists("An active user with this username/email already exists.")

        if not db_user:
            new_db_user = UserCreate(username=user.username, password=get_password_hash(user.password), email=user.email)
            user = self.user_db_model_service.create_user(user=new_db_user)
            return user

        if db_user:
            db_user = self.user_db_model_service.activate_user(db_user=db_user)
            return db_user

    def get_user(self, username: str) -> User:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        with tracer.start_as_current_span(f"UserServiceManager.get_user.{username}"):
            logger.info(f"Trying to fetch user details from db", extra={"username": username})
            db_user = self.user_db_model_service.get_user(username=username)
            if not db_user:
                raise InactiveUser("No user was found with this username.")
            return db_user

    def get_active_user(self, username: str) -> User:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        db_user = self.user_db_model_service.get_active_user(username=username)
        if not db_user:
            raise InactiveUser("No active user was found with this username.")
        return db_user

    def delete_user(self, username: str):
        """
        Deletes a user from the database.

        Args:
            db (Session): The database session.
            db_user: The user to delete from the database.
        """
        deleted_db_user = self.user_db_model_service.delete_user(username=username)
        return deleted_db_user
