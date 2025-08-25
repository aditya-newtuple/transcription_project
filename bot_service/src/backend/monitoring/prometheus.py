import shutil
from pathlib import Path
from prometheus_client import CollectorRegistry, Counter, Gauge, Info, Summary

registry = CollectorRegistry()

REQUEST_COUNT = Counter("app_request_count", "Application Request Count", ["method", "endpoint", "http_status"])

SYSTEM_USAGE = Gauge("system_usage", "Hold current system resource usage", ["resource_type"])

# Disk space gauges
DISK_TOTAL = Gauge("disk_total_bytes", "Total disk space in bytes")
DISK_USED = Gauge("disk_used_bytes", "Used disk space in bytes")
DISK_FREE = Gauge("disk_free_bytes", "Free disk space in bytes")
DISK_PERCENTAGE = Gauge("disk_usage_percentage", "Disk usage percentage")

REQUEST_TIME = Summary("response_latency_seconds", "Response latency (seconds)")

OPERATION_TIME = Summary("operation_latency_seconds", "Operation Request Latency", ["operation", "type"])

CLASSIFY_EXTRACT_TIME = Summary("ce_operation_latency_seconds", "Operation Request Latency", ["operation", "type", "meta_id"])

INFO = Info("my_build", "Description of info")
INFO.info({"app_version": "0.01", "app_name": "bot_service", "environment": "dev"})

def update_disk_metrics():
    """Update disk space metrics"""
    try:
        # Get the path where files are stored
        storage_path = Path("/Users/sharadhake/Desktop/local-transcription-hilliard/Main_Project/grapheus-scribe/bot_service/src/backend/etc")
        
        # Get disk usage statistics
        total, used, free = shutil.disk_usage(storage_path)
        
        # Update Prometheus metrics
        DISK_TOTAL.set(total)
        DISK_USED.set(used)
        DISK_FREE.set(free)
        
        # Calculate and set percentage
        percentage = (used / total) * 100 if total > 0 else 0
        DISK_PERCENTAGE.set(percentage)
        
        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "percentage": round(percentage, 1),
            "status": "healthy" if percentage < 60 else "warning" if percentage < 80 else "critical"
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percentage": 0,
            "status": "error"
        }
