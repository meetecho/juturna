from fastapi import HTTPException

from juturna.names import ServiceFailureReason
from juturna.models.api import UnsuccessfulResponse

FAILURE_STATUS_CODES = {
    ServiceFailureReason.ALREADY_RUNNING: 409,
    ServiceFailureReason.ALREADY_WARMEDUP: 409,
    ServiceFailureReason.NOT_READY: 409,
    ServiceFailureReason.NOT_RUNNING: 409,
    ServiceFailureReason.INVALID_ID: 400,
    ServiceFailureReason.INTERNAL_ERROR: 500,
}


def raise_on_unsuccessful_response(response: UnsuccessfulResponse):
    """
    Raises a HTTPException with appropriate code,
    based on UnsuccessfulResponse.reason property

    Args:
        response (UnsuccessfulResponse): unsuccessful response model

    Raises:
        HTTPException

    """
    raise HTTPException(
        FAILURE_STATUS_CODES.get(response.reason), detail=response.model_dump()
    )
