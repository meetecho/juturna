from enum import StrEnum
from enum import unique


@unique
class ServiceStatus(StrEnum):
    REQUEST_OK       = 'service_request_ok'
    REQUEST_KO       = 'service_request_failed'
    INVALID_ID       = 'session_id_invalid'
    ALREADY_WARMEDUP = 'session_already_warmedup'
    ALREADY_RUNNING  = 'session_already_running'
    NOT_READY        = 'session_not_ready'
    NOT_RUNNING      = 'session_not_running'
