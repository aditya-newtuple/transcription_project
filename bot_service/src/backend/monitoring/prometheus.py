from prometheus_client import CollectorRegistry, Counter, Gauge, Info, Summary

registry = CollectorRegistry()

REQUEST_COUNT = Counter("app_request_count", "Application Request Count", ["method", "endpoint", "http_status"])

SYSTEM_USAGE = Gauge("system_usage", "Hold current system resource usage", ["resource_type"])

REQUEST_TIME = Summary("response_latency_seconds", "Response latency (seconds)")

OPERATION_TIME = Summary("operation_latency_seconds", "Operation Request Latency", ["operation", "type"])

CLASSIFY_EXTRACT_TIME = Summary("ce_operation_latency_seconds", "Operation Request Latency", ["operation", "type", "meta_id"])

INFO = Info("my_build", "Description of info")
INFO.info({"app_version": "0.01", "app_name": "bot_service", "environment": "dev"})
