import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    Compression,
)
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as OTLPGRPCLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as OTLPHTTPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from pythonjsonlogger import jsonlogger

# Set up the logger


class SpanFormatter(logging.Formatter):
    """Formatter that adds trace and span IDs to log records."""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self._current_trace_id = None
        self._current_span_id = None

    def format(self, record: logging.LogRecord):
        """Format the log record to include trace and span IDs."""
        span = trace.get_current_span()
        context = span.get_span_context()

        trace_id = context.trace_id
        span_id = context.span_id

        self._current_trace_id = "{trace:032x}".format(trace=trace_id)
        self._current_span_id = "{span:016x}".format(span=span_id)
        record.trace_id = self._current_trace_id
        record.span_id = self._current_span_id

        # Handle multiline messages by adding trace info to each line
        if record.exc_info:
            record.exc_text = "\n".join([f"[trace_id: {self._current_trace_id}][span_id: {self._current_span_id}] {line}" for line in self.formatException(record.exc_info).split("\n")])

        return super().format(record)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for log records."""

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        span = trace.get_current_span()

        if span:
            span_context = span.get_span_context()
            log_record["trace_id"] = "{trace:032x}".format(trace=span_context.trace_id)
            log_record["span_id"] = "{span:016x}".format(span=span_context.span_id)
        else:
            log_record["trace_id"] = None
            log_record["span_id"] = None

        # Handle multiline messages by adding trace info to each line
        if "exc_info" in message_dict:
            if isinstance(message_dict["exc_info"], str):
                lines = message_dict["exc_info"].split("\n")
                message_dict["exc_info"] = "\n".join([f"[trace_id: {log_record.get('trace_id')}][span_id: {log_record.get('span_id')}] {line}" for line in lines])


class Logger:

    def __init__(self):
        """Initialize the logger."""
        self.ENABLE_OTEL_COLLECTOR = os.getenv("ENABLE_OTEL_COLLECTOR", "False").lower() in ("true", "1", "t")
        self.ENABLE_JSON_LOGGER = os.getenv("ENABLE_JSON_LOGGER", "False").lower() in ("true", "1", "t")
        self.logger = logging.getLogger("__name__")
        logs_path = Path("./logs")
        logs_dir_path = logs_path.cwd().parent / "logs"
        logs_dir_path.mkdir(exist_ok=True, parents=True)

        self.tracer = trace.get_tracer(__name__)
        # shell_handler = RichHandler(console=Console(width=terminal_width))
        self.shell_handler = logging.StreamHandler()
        self.file_handler = TimedRotatingFileHandler(logs_dir_path / "logger.log", when="midnight", backupCount=30)
        self.file_handler.suffix = r"%Y-%m-%d.log"

        self.fmt_shell = "%(message)s"
        self.fmt_file = "%(levelname)4s %(asctime)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
        self.otel_fmt_file = "%(levelname)4s %(asctime)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s [trace_id: %(trace_id)s%(span_id)s][span_id: %(span_id)s] "

        self.set_level(self.logger, logging.DEBUG)
        self.set_level(self.shell_handler, logging.DEBUG)
        self.set_level(self.file_handler, logging.DEBUG)

        # Set formatters for shell and file
        # self.set_formatter(self.logger, self.otel_fmt_file)

        self.set_formatter(self.shell_handler, self.otel_fmt_file)
        self.set_formatter(self.file_handler, self.otel_fmt_file)

        # self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.shell_handler)

        if self.ENABLE_JSON_LOGGER:
            self.enable_json_logger(self.shell_handler, self.otel_fmt_file)

        if self.ENABLE_OTEL_COLLECTOR:
            self.enable_otel()

    def get_logger(self):
        """
        Get the logger instance.
        """
        return self.logger

    def get_trace(self):
        """
        Get the tracer instance.
        """
        return self.tracer

    def set_level(self, logger: logging.Handler, level):
        """
        Set the logging level for the specified logger.
        """
        logger.setLevel(level)

    def set_formatter(self, logger: logging.Handler, formatter):
        """
        Set the formatter for the specified logger.
        """
        # parsed_formatter = logging.Formatter(formatter)
        # logger.setFormatter((parsed_formatter))
        logger.setFormatter(SpanFormatter(formatter))

    def enable_json_logger(self, logger: logging.Handler, formatter):
        """
        Enable JSON logging for the specified logger.
        """
        logger.setFormatter(CustomJsonFormatter(formatter))

    def enable_otel(self):
        """
        Enable OpenTelemetry tracing.
        """
        OTEL_AGENT_HOSTNAME = os.environ.get("OTEL_AGENT_HOSTNAME", "http://localhost")
        HTTP_OTEL_AGENT_PORT = os.environ.get("OTEL_HTTP_AGENT_PORT", "4318")
        GRPC_OTEL_AGENT_PORT = os.environ.get("OTEL_GRPC_AGENT_PORT", "4317")

        trace.set_tracer_provider(TracerProvider())
        tracer_provider: TracerProvider = trace.get_tracer_provider()
        otlp_span_exporter = OTLPGRPCSpanExporter(endpoint=f"{OTEL_AGENT_HOSTNAME}:{GRPC_OTEL_AGENT_PORT}", insecure=True, compression=Compression.Gzip.value)
        # span_processor = BatchSpanProcessor(otlp_span_exporter)
        # tracer_provider.add_span_processor(span_processor)

        resource = Resource(attributes={f"service.application_name": os.environ.get("APPLICATION_NAME", "local"), f"service.environment": os.environ.get("ENVIRONMENT", "local")})

        # Create and set the logger provider
        logger_provider = LoggerProvider(resource)
        set_logger_provider(logger_provider)

        # Create the OTLP log exporter that sends logs to configured destination
        http_exporter = OTLPHTTPLogExporter(endpoint=f"{OTEL_AGENT_HOSTNAME}:{HTTP_OTEL_AGENT_PORT}/v1/logs", compression=Compression.Gzip)
        grpc_exporter = OTLPGRPCLogExporter(endpoint=f"{OTEL_AGENT_HOSTNAME}:{GRPC_OTEL_AGENT_PORT}", insecure=True, compression=Compression.Gzip.value)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(grpc_exporter))

        # Attach OTLP handler to root logger
        handler = LoggingHandler(logging.DEBUG, logger_provider=logger_provider)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(SpanFormatter(self.otel_fmt_file))

        # ENABLE/DISABLE JSON LOGGER
        # handler.setFormatter(CustomJsonFormatter(self.otel_fmt_file))
        # self.shell_handler.setFormatter(
        #     CustomJsonFormatter(self.otel_fmt_file))

        self.logger.addHandler(handler)


# Create a global logger instance to maintain backward compatibility
# env_path = Path("./etc/.envc")
# sample_env_path = Path("./env_sample")

# if not env_path.exists():
#    print(f'Loading sample .env file from {sample_env_path}.')
#    load_dotenv(sample_env_path)
# else:
#     load_dotenv(env_path)
#     print(f"Using existing .env file at {env_path}.")

_logger_instance = Logger()
logger = _logger_instance.get_logger()
tracer = _logger_instance.get_trace()
