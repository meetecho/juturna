from enum import StrEnum
from enum import unique


@unique
class ServiceStatus(StrEnum):
    REQUEST_OK = 'service_request_ok'
    REQUEST_KO = 'service_request_failed'
