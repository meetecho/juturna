from enum import StrEnum
from enum import unique


@unique
class PipelineStatus(StrEnum):
    NEW = 'pipeline_created'
    READY = 'pipeline_ready'
    RUNNING = 'pipeline_running'
