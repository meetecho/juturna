from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from logging import Logger

from juturna.cli.commands.exceptions import (
    AlreadyWarmedupException,
    InvalidPipelineIdException,
    AlreadyRunningException,
    NotReadyException,
    NotRunningException,
)


def _invalid_pipeline_id_handler(
    request: Request,
    exception: InvalidPipelineIdException,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={'message': f'no pipeline with id: {exception.pipeline_id}'},
    )


def _already_warmedup_handler(
    request: Request,
    exception: AlreadyWarmedupException,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            'message': f'pipeline {exception.pipeline_id} already warmed up'
        },
    )


def _already_running_handler(
    request: Request,
    exception: AlreadyRunningException,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            'message': f'pipeline {exception.pipeline_id} already running'
        },
    )


def _not_ready_handler(
    request: Request, exception: NotReadyException
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': f'pipeline {exception.pipeline_id} is not ready'},
    )


def _not_running_handler(
    request: Request, exception: NotRunningException
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'message': f'pipeline {exception.pipeline_id} is not running'},
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
        - AlreadyWarmedupException
        - AlreadyRunningException
        - NotReadyException
        - NotRunningException

    Args:
        app (FastAPI): Fastapi instance to apply handlers to

    """
    app.add_exception_handler(
        InvalidPipelineIdException, _invalid_pipeline_id_handler
    )
    app.add_exception_handler(
        AlreadyWarmedupException, _already_warmedup_handler
    )

    app.add_exception_handler(AlreadyRunningException, _already_running_handler)

    app.add_exception_handler(NotReadyException, _not_ready_handler)

    app.add_exception_handler(NotRunningException, _not_running_handler)


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
