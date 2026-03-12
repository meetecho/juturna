"""Response classes for JuturnaService component"""

from pydantic import BaseModel

from juturna.names import PipelineStatus
from juturna.names import ServiceStatus
from juturna.names import ServiceFailureReason


class SuccessfulResponse(BaseModel):
    """Successful Response Model"""

    status: str = ServiceStatus.REQUEST_OK


class UnsuccessfulResponse(BaseModel):
    """Unsuccesful Response Model"""

    status: str = ServiceStatus.REQUEST_KO
    reason: ServiceFailureReason
    detail: str = ''


class PipelineCreatedResponse(SuccessfulResponse):
    """Successful Response for Pipeline creation methods"""

    pipeline_id: str
    created_at: float
    status: PipelineStatus
