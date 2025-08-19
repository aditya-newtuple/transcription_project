from enum import Enum, StrEnum
from typing import Any, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class ExtendedEnum(Enum):
    """Extended Enum class with a method to list all values."""

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class ExtendedStrEnum(StrEnum):
    """Extended StrEnum class with a method to list all values."""

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class BaseModel(PydanticBaseModel):
    """Base model for all data models"""

    model_config = ConfigDict(
        populate_by_name=True,
        # validate_assignment=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
    )


class LoggerConfiguration(BaseModel):
    """Represents the logger configuration"""

    log_level: str


class ServerConfiguration(BaseModel):
    """Represents the server configuration"""

    host: str
    port: str


class OpenAIConfiguration(BaseModel):
    """Represents the OpenAI configuration"""

    api_key: str
    model_name: str
    embedding_model_name: str
    context_window: int


class AzureAIConfiguration(BaseModel):
    """Represents the AzureAI configuration"""

    api_key: str
    type: str
    base: str
    version: str
    deployment_name: str
    embedding_deployment_name: str
    model_name: str


class PerplexityAIConfiguration(BaseModel):
    """Represents the Perplexity configuration"""

    api_key: str
    model_name: str
    api_base: str


class AnthropicAIConfiguration(BaseModel):
    """Represents the Anthropic configuration"""

    api_key: str
    model_name: str


class GeminiAIConfiguration(BaseModel):
    """Represents the Anthropic configuration"""

    api_key: str
    model_name: str


class MongoDBConfiguration(BaseModel):
    """Represents the MongoDB configuration"""

    host: str
    port: int
    username: str
    password: str
    db: str


class PostgreSQLConfiguration(BaseModel):
    """Represents the PostgreSQL configuration"""

    host: str
    port: int
    username: str
    password: str
    db: str
    app_schema: str


class SQLServerConfiguration(BaseModel):
    """Represents the SQLServer configuration"""

    host: str
    port: int
    username: str
    password: str
    db: str
    app_schema: str


class SQLiteConfiguration(BaseModel):
    """Represents the SQLite configuration"""

    db_path: str


class OpenSearchConfiguration(BaseModel):
    """Represents the OpenSearch configuration"""

    host: str
    username: str
    password: str
    use_ssl: bool
    verify_certs: bool
    index_name: str


class LangfuseConfiguration(BaseModel):
    """Represents the Langfuse configuration"""

    env: str


class CommonConfiguration(BaseModel):
    """Represents the common configuration"""

    max_retries: int


class PocketBaseConfiguration(BaseModel):
    """Represents the PocketBase configuration"""

    url: str
    admin_email: str
    admin_password: str


# class AWSConfiguration(BaseModel):
#     """Represents the AWS configuration"""

#     aws_access_key_id: str
#     aws_secret_access_key: str


class PineconeConfiguation(BaseModel):
    """Represents the Pinecone configuration"""

    api_key: str
    index: str
    namespace: str
    spec_cloud: str
    spec_region: str
    metric: str
    timeout: int


class AzureAISearchConfiguration(BaseModel):
    """Represents the AzureAISearch configuration"""

    endpoint: str
    key: str
    index_name: str
    semantic_configuration_name: str


class ObservabilityConfiguration(BaseModel):
    """Represents the Observability configuration"""

    enable_json_logger: bool
    enable_otel_collector: bool
    otel_agent_hostname: str
    otel_http_agent_port: int
    otel_grpc_agent_port: int


class TranscriberConfiguration(BaseModel):
    """Represents the Transcriber service configuration"""

    model_name: str = "large-v2"
    device: str = "cpu"
    compute_type: str = "int8"
    models_directory: Optional[str] = None


class Configuration(BaseModel):
    """Represents the configuration"""

    application_name: str
    environment: str
    logger_configuration: LoggerConfiguration
    openai_configuration: OpenAIConfiguration
    server_configuration: ServerConfiguration

    azureai_configuration: AzureAIConfiguration
    perplexityai_configuration: PerplexityAIConfiguration
    anthropicai_configuration: AnthropicAIConfiguration
    geminiai_configuration: GeminiAIConfiguration
    common_configuration: CommonConfiguration
    mongodb_configuration: MongoDBConfiguration
    postgresql_configuration: PostgreSQLConfiguration
    sqlserver_configuration: SQLServerConfiguration
    sqlite_configuration: SQLiteConfiguration
    opensearch_configuration: OpenSearchConfiguration
    
    transcriber_configuration: TranscriberConfiguration

    pinecone_configuration: PineconeConfiguation

    langfuse_configuration: LangfuseConfiguration
    pocketbase_configuration: PocketBaseConfiguration
    observability_configuration: ObservabilityConfiguration


class LangfuseMetaData(BaseModel):
    """Represents the metadata for Langfuse generations"""

    generation_name: str = None
    generation_id: str = None
    parent_observation_id: str = None
    version: str = None
    trace_user_id: str = None
    session_id: str = None
    tags: list[str] = None
    trace_name: str = None
    trace_id: str = None
    trace_metadata: dict[str, Any] = None
    trace_version: str = None
    trace_release: str = None
    existing_trace_id: Optional[str] = None
    update_trace_keys: Optional[list[str]] = None
    debug_langfuse: Optional[bool] = None
    mask_input: Optional[bool] = None


class QueryContext(BaseModel):
    """Represents the query context"""

    query: str
    role: str
    stream_response: Any


# region Constants


class Roles(ExtendedStrEnum):
    "Represents roles"

    admin = "Admin"
    basic = "Basic"
    Developer = "Developer"


class LLMProvider(ExtendedStrEnum):
    "Represents provider"

    openai = "openai"
    bedrock = "bedrock"
    azure_openai = "azure_openai"
    perplexity_ai = "perplexity_ai"
    anthropic_ai = "anthropic_ai"
    gemini_ai = "gemini_ai"
    lite_llm = "lite_llm"


class LiteLLMModels(ExtendedStrEnum):
    "Represents lite llm models"

    gpt_4o = "gpt-4o"
    gpt_4o_mini = "gpt-4o-mini"
    bedrock_anthropic_claude_sonnet = "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0"
    gemini_flash = "gemini/gemini-2.0-flash"


class LangfusePrompt(ExtendedStrEnum):
    "Represents llm prompts"

    search_eval = "search_eval"
    search_eval_compare = "search_eval_compare"
    global_search = "global_search"
    generator = "generator"
    sql_agent = "sql_agent"
    mongo_agent = "mongo_agent"


class DatabaseType(ExtendedStrEnum):
    "Represents different database types"

    postgresql = "postgresql"
    pinecone = "pinecone"
    azure_ai_search = "azure_ai_search"
    chroma = "chroma"


class VectorDBModel(ExtendedStrEnum):
    pinecone = "pinecone"
    azure_ai_search = "azure_ai_search"


# endregion
