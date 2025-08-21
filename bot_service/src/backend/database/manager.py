from contextlib import contextmanager
from typing import Any, Dict, List, Generator

from common.configuration import Configuration
from common.data_model import (  # SQLServerConfiguration,
    PostgreSQLConfiguration,
    SQLiteConfiguration,
)
from common.logger import logger
from common.redis import RedisManager
from exceptions.db import DBException
from opensearchpy import OpenSearch, RequestsHttpConnection
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import (
    CompileError,
    DatabaseError,
    NoSuchTableError,
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.schema import CreateTable

# Create Base class for SQLAlchemy models
Base = declarative_base()

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class OpenSearchDBService:
    def __init__(self, config: Configuration) -> None:
        """
        Initialize OpenSearchDBService with configuration.

        Args:
            config: Application configuration
        """
        super().__init__()

        # Initialize basic attributes
        self._index = None
        self._vector_store = None
        self._query_engine = None
        self.config = config

        # Initialize OpenSearch client
        self.client = OpenSearch(
            hosts=[config.configuration().opensearch_configuration.host],
            http_auth=(config.configuration().opensearch_configuration.username, config.configuration().opensearch_configuration.password),
            use_ssl=config.configuration().opensearch_configuration.use_ssl,
            verify_certs=config.configuration().opensearch_configuration.verify_certs,
            connection_class=RequestsHttpConnection,
        )

    def create_index(self, index_name: str, mapping: Dict[str, Any]):
        """Creates an index with the specified mapping"""
        try:

            if index_name not in self.get_all_indices():
                response = self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"Successfully created index: {index_name}")
                return response
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            # to-do - replace with custom exception
            raise ValueError(f"Failed to create index: {str(e)}")

    def get_all_indices(self) -> List[str]:
        """Returns list of all indices"""
        try:
            indices = self.client.indices.get_alias().keys()
            return list(indices)
        except Exception as e:
            logger.error(f"Could not get indices due to {e}")
            return []

    def get_index_mapping(self, index_name: str) -> Dict[str, Any]:
        """Returns mapping for specified index"""
        try:
            mapping = self.client.indices.get_mapping(index=index_name)
            return mapping
        except Exception as e:
            logger.error(f"Could not get mapping for index {index_name} due to {e}")
            return {}

    def bulk_index_documents(self, index_name: str, document_chunks_with_metadata: Dict[str, List], batch_size: int = 1000):
        """
        Bulk indexes documents with their embeddings.

        Args:
            index_name: Name of the index to store documents
            document_chunks_with_metadata: Dictionary mapping filenames to their chunks with metadata and embeddings
            batch_size: Number of documents to index in each batch
        """
        try:
            # First create the index with mapping if it doesn't exist
            mapping = {
                "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1, "knn": True, "knn.algo_param.ef_search": 100}},
                "mappings": {
                    "properties": {
                        "file_name": {"type": "keyword"},
                        "page_content": {"type": "text"},
                        "level_1": {"type": "keyword"},
                        "level_2": {"type": "keyword"},
                        "level_3": {"type": "keyword"},
                        "metadata": {
                            "properties": {
                                "page_label": {"type": "keyword"},
                                "file_path": {"type": "keyword"},
                                "file_type": {"type": "keyword"},
                                "file_size": {"type": "long"},
                                "creation_date": {"type": "date"},
                                "last_modified_date": {"type": "date"},
                            }
                        },
                        "embedding": {"type": "knn_vector", "dimension": 1536, "method": {"name": "hnsw", "space_type": "l2", "engine": "nmslib", "parameters": {"ef_construction": 128, "m": 16}}},
                    }
                },
            }

            self.create_index(index_name, mapping)

            # Prepare bulk indexing data
            bulk_data = []
            total_chunks = sum(len(chunks) for chunks in document_chunks_with_metadata.values())
            processed_chunks = 0

            for file_name, chunks in document_chunks_with_metadata.items():
                for i, chunk in enumerate(chunks):
                    # Convert embedding values to float
                    embedding = [float(x) for x in chunk["embedding"]]

                    # Verify embedding dimension
                    if len(embedding) != 1536:
                        raise ValueError(f"Embedding dimension mismatch. Expected 1024, got {len(embedding)}")

                    # Action metadata
                    action = {"index": {"_index": index_name, "_id": f"{file_name}-{i}"}}

                    # Document data
                    doc = {
                        "file_name": file_name,
                        "page_content": chunk["page_content"],
                        "embedding": embedding,
                        "metadata": chunk["metadata"],
                        "level_1": chunk["level_1"],
                        "level_2": chunk["level_2"],
                        "level_3": chunk["level_3"],
                    }

                    bulk_data.append(action)
                    bulk_data.append(doc)
                    processed_chunks += 1

                    # Index in batches
                    if len(bulk_data) >= batch_size * 2:  # multiply by 2 because each doc has action + data
                        response = self.client.bulk(index=index_name, body=bulk_data, timeout=300)
                        if response.get("errors"):
                            logger.error(f"Errors occurred during bulk indexing: {response}")
                        logger.info(f"Indexed {processed_chunks}/{total_chunks} chunks")
                        bulk_data = []

            # Index remaining documents
            if bulk_data:
                response = self.client.bulk(index=index_name, body=bulk_data, timeout=300)
                if response.get("errors"):
                    logger.error(f"Errors occurred during bulk indexing: {response}")

            logger.info(f"Successfully indexed {total_chunks} chunks from {len(document_chunks_with_metadata)} files")

        except Exception as e:
            logger.error(f"Error during bulk indexing: {str(e)}")
            raise ValueError(f"Failed to bulk index documents: {str(e)}")

    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Returns statistics for the specified index"""
        try:
            stats = self.client.indices.stats(index=index_name)
            return stats
        except Exception as e:
            logger.error(f"Could not get index stats due to {e}")
            return {}

    def delete_vectors_by_file_name(self, index_name: str, file_name: str) -> Dict[str, Any]:
        """
        Deletes all documents from the index with the specified file_name.

        Args:
            index_name: Name of the index to delete documents from
            file_name: The file_name to match for deletion

        Returns:
            Response from the delete operation
        """
        try:
            query = {"query": {"term": {"file_name": file_name}}}

            response = self.client.delete_by_query(index=index_name, body=query)

            logger.info(f"Successfully deleted documents with file_name: {file_name} from index: {index_name}")
            return response
        except Exception as e:
            logger.error(f"Error deleting documents with file_name {file_name} from index {index_name}: {str(e)}")
            raise ValueError(f"Error deleting documents with file_name {file_name} from index {index_name}: {str(e)}")


class PostgresDBService:
    def __init__(self, config: Configuration) -> None:
        """Initialize the PostgresDBService."""
        super().__init__()

        SQLALCHEMY_DATABASE_URL = URL.create(
            drivername="postgresql",
            username=config.configuration().postgresql_configuration.username,
            password=config.configuration().postgresql_configuration.password,
            host=config.configuration().postgresql_configuration.host,
            port=config.configuration().postgresql_configuration.port,
            database=config.configuration().postgresql_configuration.db,
        )
        self.engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self.base = declarative_base()

    def get_custom_conn(self, config: PostgreSQLConfiguration):
        """Get custom database connection."""
        SQLALCHEMY_DATABASE_URL = URL.create(
            drivername="postgresql",
            username=config.username,
            password=config.password,
            host=config.host,
            port=config.port,
            database=config.db,
        )
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        return engine, declarative_base()

    def get_db_session(self):
        """
        Get a database session.
        """
        sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
        db = sessionlocal()
        return db

    @contextmanager
    def get_custom_db_contxt_session(self, engine: Engine):
        """Creates a context with an open SQLAlchemy session."""
        connection = None
        db_session = None
        try:
            connection = engine.connect()
            db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine, expire_on_commit=False))
            yield db_session
        except (OperationalError, SQLAlchemyError, ProgrammingError, NoSuchTableError, CompileError, DatabaseError, DBException) as e:
            if db_session:
                db_session.rollback()
            raise DBException(f"Unable to perform PostgreSQL db operation due to error {e}, rolling back")
        finally:
            errors = []
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    errors.append(e)
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    errors.append(e)
            if errors:
                logger.error(f"Failed to close connection and session due to {errors}")
                raise SQLAlchemyError(f"Failed to close connection and session due to {errors}")

    def get_all_table_ddls(self, engine: Engine):
        """
        Get all table DDLs.
        """
        try:
            table_ddls = []
            meta = MetaData()
            meta.reflect(bind=engine)

            for table in meta.sorted_tables:
                table_ddls.append(CreateTable(table).compile(engine).string)

            return table_ddls
        except BaseException as e:
            logger.error(f"Could not get table ddls due to {e}")
            return []

    def get_all_tables(self, engine: Engine):
        """
        Get all table names.
        """
        try:
            meta = MetaData()
            meta.reflect(bind=engine)
            return list(meta.tables)
        except BaseException as e:
            logger.error(f"Could not get table ddls due to {e}")
            return []


# class SQLServerDBService:
#     def __init__(self, config: Configuration) -> None:
#         super().__init__()

#         SQLALCHEMY_DATABASE_URL = URL.create(
#             drivername="mssql+pyodbc",
#             username=config.configuration().sqlserver_configuration.username,
#             password=config.configuration().sqlserver_configuration.password,
#             host=config.configuration().sqlserver_configuration.host,
#             port=config.configuration().sqlserver_configuration.port,
#             database=config.configuration().sqlserver_configuration.db,
#             query={
#                 "driver": "ODBC Driver 18 for SQL Server",
#                 "TrustServerCertificate": "yes",
#                 "application_name": "app",
#                 "ConnectRetryCount": "4",
#                 "ConnectRetryInterval": "5",
#                 "ConnectionTimeout": "5",
#                 "Connection Timeout": "120",
#                 "Timeout": "120",
#             },
#         )

#         self.engine = create_engine(
#             SQLALCHEMY_DATABASE_URL,
#             pool_size=0,
#             # max_overflow=10,
#             pool_pre_ping=True,
#         )
#         self.base = declarative_base()

#     def get_custom_conn(self, config: SQLServerConfiguration):
#         SQLALCHEMY_DATABASE_URL = URL.create(
#             drivername="mssql+pyodbc",
#             username=config.username,
#             password=config.password,
#             host=config.host,
#             port=config.port,
#             database=config.db,
#             query={
#                 "driver": "ODBC Driver 18 for SQL Server",
#                 "TrustServerCertificate": "yes",
#                 "application_name": "app",
#                 "ConnectRetryCount": "4",
#                 "ConnectRetryInterval": "5",
#                 "ConnectionTimeout": "5",
#                 "Connection Timeout": "120",
#                 "Timeout": "120",
#             },
#         )
#         engine = create_engine(
#             SQLALCHEMY_DATABASE_URL,
#             pool_size=5,
#             max_overflow=10,
#             pool_pre_ping=True,
#         )
#         return engine, declarative_base()

#     def get_db_session(self):
#         sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
#         db = sessionlocal()
#         return db

#     @contextmanager
#     def get_custom_db_contxt_session(self, engine: Engine):
#         """Creates a context with an open SQLAlchemy session."""
#         try:
#             connection = engine.connect()
#             db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine, expire_on_commit=False))
#             yield db_session
#         except (OperationalError, SQLAlchemyError, ProgrammingError, NoSuchTableError, CompileError, DatabaseError, DBException) as e:
#             db_session.rollback()
#             raise DBException(f"Unable to perform SQLServer db operation due to error {e}, rolling back")
#         finally:
#             errors = []
#             try:
#                 db_session.close()
#             except Exception as e:
#                 errors.append(e)
#             try:
#                 connection.close()
#             except Exception as e:
#                 errors.append(e)
#             if errors:
#                 logger.error(f"Failed to close connection and session due to {errors}")
#                 raise SQLAlchemyError(f"Failed to close connection and session due to {errors}")

#     def get_all_table_ddls(self, engine: Engine):
#         try:
#             table_ddls = []
#             meta = MetaData()
#             meta.reflect(bind=engine)

#             for table in meta.sorted_tables:
#                 table_ddls.append(CreateTable(table).compile(engine).string)

#             return table_ddls
#         except BaseException as e:
#             logger.error(f"Could not get table ddls due to {e}")
#             return []

#     def get_all_tables(self, engine: Engine):
#         try:
#             meta = MetaData()
#             meta.reflect(bind=engine)
#             return list(meta.tables)
#         except BaseException as e:
#             logger.error(f"Could not get table names due to {e}")
#             return []


class SQLiteDBService:
    def __init__(self, config: Configuration) -> None:
        """Get the SQLite database engine."""
        super().__init__()

        SQLALCHEMY_DATABASE_URL = URL.create(drivername="sqlite", database=config.configuration().sqlite_configuration.db_path)

        self.engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
        self.base = declarative_base()

    def get_custom_conn(self, config: SQLiteConfiguration):
        """
        Get a custom SQLite database connection.
        """
        SQLALCHEMY_DATABASE_URL = URL.create(drivername="sqlite", database=config.db_path)
        engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
        return engine, declarative_base()

    def get_db_session(self):
        """
        Get a database session.
        """
        sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
        db = sessionlocal()
        return db

    @contextmanager
    def get_custom_db_contxt_session(self, engine: Engine):
        """Creates a context with an open SQLAlchemy session."""
        try:
            connection = engine.connect()
            db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine, expire_on_commit=False))
            yield db_session
        except (OperationalError, SQLAlchemyError, ProgrammingError, NoSuchTableError, CompileError, DatabaseError, DBException) as e:
            db_session.rollback()
            raise DBException(f"Unable to perform SQLite db operation due to error {e}, rolling back")
        finally:
            db_session.close()
            connection.close()

    def get_all_table_ddls(self, engine: Engine):
        """
        Get all table DDLs.
        """
        try:
            table_ddls = []
            meta = MetaData()
            meta.reflect(bind=engine)

            for table in meta.sorted_tables:
                table_ddls.append(CreateTable(table).compile(engine).string)

            return table_ddls
        except Exception as e:
            logger.error(f"Could not get table ddls due to {e}")
            return []

    def get_all_tables(self, engine: Engine):
        """
        Get all table names.
        """
        try:
            meta = MetaData()
            meta.reflect(bind=engine)
            return list(meta.tables)
        except Exception as e:
            logger.error(f"Could not get table names due to {e}")
            return []


class DatabaseServiceManager:
    """
    Manager for the database service.
    """

    def __init__(self, config: Configuration):
        self._postgres_db_service = PostgresDBService(config)
        self._opensearch_db_service = OpenSearchDBService(config)
        self._redis_service = RedisManager(config)
        # self._sqlserver_db_service = SQLServerDBService(config)
        self._sqlite_db_service = SQLiteDBService(config)

        # Initialize the main database engine and bind it to SessionLocal
        global SessionLocal
        SessionLocal.configure(bind=self._postgres_db_service.engine)

    def postgres_db_service(self) -> PostgresDBService:
        """Get the Postgres database service."""
        return self._postgres_db_service

    def opensearch_db_service(self) -> OpenSearchDBService:
        """Get the OpenSearch database service."""
        return self._opensearch_db_service

    def redis_service(self) -> RedisManager:
        """Get the Redis service."""
        return self._redis_service

    # def sqlserver_db_service(self) -> SQLServerDBService:
    #     return self._sqlserver_db_service

    def sqlite_db_service(self) -> SQLiteDBService:
        """Get the SQLite database service."""
        return self._sqlite_db_service
