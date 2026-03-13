from enum import StrEnum
from enum import unique


@unique
class ServiceFailureReason(StrEnum):
    INVALID_ID = 'pipeline_id_invalid'
    ALREADY_WARMEDUP = 'pipeline_already_warmedup'
    ALREADY_RUNNING = 'pipeline_already_running'
    NOT_READY = 'pipeline_not_warmed_up'
    NOT_RUNNING = 'pipeline_not_running'
    INTERNAL_ERROR = 'pipeline_internal_error'
