from datetime import UTC, datetime

from common.logger import logger, tracer
from database.manager import DatabaseServiceManager
from exceptions.db import DBException
from exceptions.user import InactiveUser
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from user.models.interface import UserCreate

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(2000), unique=True)
    username = Column(String(2000), unique=True)
    hashed_password = Column(String(2000))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
    meta_data = Column(JSON, nullable=True)

    # threads = relationship("Thread", back_populates="user")
    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class UserModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

        try:
            if Base:
                logger.critical("Trying creating base tables for users..", extra={"tags": "create_base_tables"})
                Base.metadata.create_all(bind=self.current_db_engine)

        except BaseException as e:
            error = {"error": e}
            logger.critical(f"Could not create base tables for users due to \n {error}, db operations won't work!")

    def get_user(self, username: str = None):
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with tracer.start_as_current_span(f"UserServiceManager.get_user.{username}"):
                logger.info(f"Fetching user details from db", extra={"username": username})
                with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                    db_user = db.query(User).filter(User.username == username).first()
                    return db_user
        except DBException as e:
            raise DBException(f"Could not get user due to {e}")

    def get_active_user(self, username: str = None):
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
                return db_user
        except DBException as e:
            raise DBException(f"Could not get active user due to {e}")

    def get_user_by_email(self, email: str = None):
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == email).first()
                return db_user

        except DBException as e:
            raise DBException(f"Could not get user by email due to {e}")

    def create_user(self, user: UserCreate) -> User:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = User(
                    # email=1, # Uncomment this line to test the simulate db error
                    email=user.email,
                    username=user.username,
                    hashed_password=user.password,
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                return db_user
        except DBException as e:
            raise DBException(f"Could not create user due to {e}")

    def delete_user(self, username: str):
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.username == username, User.is_active == True).first()

                if not db_user:
                    raise InactiveUser("No user was found with this username.")

                db_user.is_active = False
                db_user.updated_at = datetime.now(UTC)
                db.commit()
                db.refresh(db_user)
                return db_user
        except DBException as e:
            raise DBException(f"Could not delete user due to {str(e)}")

    def activate_user(self, db_user):
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user: User
                db_user.is_active = True
                db_user.updated_at = datetime.now(UTC)
                db.commit()
                db.refresh(db_user)
                return db_user
        except DBException as e:
            raise DBException(f"Could not activate user due to {str(e)}")
