"""Response classes for JuturnaService component"""

from pydantic import BaseModel, Field

from juturna.names import ServiceStatus


class SuccessfulResponse(BaseModel):
    """Successful Response Model"""

    status: str = ServiceStatus.REQUEST_OK
    data: object = Field(default={})
