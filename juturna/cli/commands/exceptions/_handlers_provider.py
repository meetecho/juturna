from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from logging import Logger

from juturna.cli.commands.exceptions import (
    InvalidPipelineIdException,
    TelemetryNotEnabledException,
    PipelineNotReadyError,
    PipelineNotRunningError,
    PipelineAlreadyRunningError,
    PipelineStoppedError,
    PipelineDestroyedError,
    PipelineBusyError,
)


def _invalid_pipeline_id_handler(
    request: Request,
    exception: InvalidPipelineIdException,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={'message': f'no pipeline with id: {exception.pipeline_id}'},
    )


def _pipeline_already_running_handler(
    request: Request,
    exception: PipelineAlreadyRunningError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _pipeline_not_ready_handler(
    request: Request, exception: PipelineNotReadyError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _pipeline_not_running_handler(
    request: Request, exception: PipelineNotRunningError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _pipeline_stopped_handler(
    request: Request, exception: PipelineStoppedError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _pipeline_destroyed_handler(
    request: Request, exception: PipelineDestroyedError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _pipeline_busy_handler(
    request: Request, exception: PipelineBusyError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': str(exception)},
    )


def _telemetry_not_enabled_handler(
    request: Request, exception: TelemetryNotEnabledException
) -> JSONResponse:
    _m = f'pipeline {exception.pipeline_id} does not have telemetry enabled'

    return JSONResponse(
        status_code=409,
        content={'message': _m},
    )


def _make_generic_exception_handler(logger: Logger):
    def _generic_exception_handler(
        request: Request, exception: Exception
    ) -> JSONResponse:
        logger.exception(f'Unexpected exception on {request.url.path}')
        exc_name = exception.__class__.__name__
        return JSONResponse(
            status_code=500,
            content={'message': f'Unexpected {exc_name} exception, see logs'},
        )

    return _generic_exception_handler


def register_pipeline_exception_handlers(app: FastAPI) -> None:
    """
    Register bundled handlers for Pipeline Exceptions:
        - InvalidPipelineIdException
        - PipelineAlreadyRunningError
        - PipelineNotReadyError
        - PipelineNotRunningError
        - PipelineStoppedError
        - PipelineDestroyedError
        - PipelineBusyError
        - TelemetryNotEnabledException

    Args:
        app (FastAPI): Fastapi instance to apply handlers to

    """
    app.add_exception_handler(
        InvalidPipelineIdException, _invalid_pipeline_id_handler
    )
    app.add_exception_handler(
        PipelineAlreadyRunningError, _pipeline_already_running_handler
    )
    app.add_exception_handler(
        PipelineNotReadyError, _pipeline_not_ready_handler
    )
    app.add_exception_handler(
        PipelineNotRunningError, _pipeline_not_running_handler
    )
    app.add_exception_handler(PipelineStoppedError, _pipeline_stopped_handler)
    app.add_exception_handler(
        PipelineDestroyedError, _pipeline_destroyed_handler
    )
    app.add_exception_handler(PipelineBusyError, _pipeline_busy_handler)
    app.add_exception_handler(
        TelemetryNotEnabledException, _telemetry_not_enabled_handler
    )


def register_generic_exception_handler(app: FastAPI, logger: Logger) -> None:
    """
    Register a generic Exception handler that logs the trace on the given logger

    Args:
        app (FastAPI): Fastapi instance to apply handler to
        logger (Logger): logger on which to log exception trace

    """
    app.add_exception_handler(
        Exception, _make_generic_exception_handler(logger)
    )
