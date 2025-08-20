from enum import Enum


class JobStatus(str, Enum):
    CREATED = 'created'
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'


class FileStatus(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'


class TranscriptFormat(str, Enum):
    TXT = 'txt'
    SRT = 'srt'
