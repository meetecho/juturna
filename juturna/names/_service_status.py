from enum import StrEnum
from enum import unique


@unique
class ServiceStatus(StrEnum):
    REQUEST_OK = 'service_request_ok'
    REQUEST_KO = 'service_request_failed'
    INVALID_ID = 'pipeline_id_invalid'
    ALREADY_WARMEDUP = 'pipeline_already_warmedup'
    ALREADY_RUNNING = 'pipeline_already_running'
    NOT_READY = 'pipeline_not_ready'
    NOT_RUNNING = 'pipeline_not_running'
