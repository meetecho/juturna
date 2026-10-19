import os
import sys
import pathlib
import json
import secrets
import ipaddress
import logging
import logging.config

from typing import Annotated

import uvicorn

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

import juturna as jt

from juturna.components._pipeline_manager import PipelineManager
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import SuccessfulResponse
from juturna.cli.commands.exceptions import (
    register_pipeline_exception_handlers,
    register_generic_exception_handler,
)

TOKEN_ENV_VAR = 'JUTURNA_SERVICE_TOKEN'

_bearer = HTTPBearer(auto_error=False)


def require_token(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
):
    """
    Reject requests without the service token as a bearer credential.

    The token is the one set by ``run()``, or ``JUTURNA_SERVICE_TOKEN`` when
    the app is served some other way. With no token configured every request
    is rejected, so the service never runs open by mistake. Browsers cannot
    attach the header to a cross-site request without a CORS preflight, so
    this also blocks cross-site requests to the state-changing routes.

    The check is skipped only when ``run()`` was called with ``auth=False``
    (``serve --no-auth``).
    """
    if not getattr(request.app.state, 'auth', True):
        return

    expected = getattr(request.app.state, 'token', None) or os.environ.get(
        TOKEN_ENV_VAR
    )

    if not expected:
        raise HTTPException(
            status_code=503, detail='service token not configured'
        )

    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail='missing or invalid service token',
            headers={'WWW-Authenticate': 'Bearer'},
        )


app = FastAPI(dependencies=[Depends(require_token)])
logger = logging.getLogger('jt.service')

# register exception handlers
register_pipeline_exception_handlers(app)
register_generic_exception_handler(app, logger)


def enable_cross_origins(app: FastAPI):
    # the token travels in the Authorization header, not in cookies, so
    # credentials are not needed (with them, "*" would reflect any origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def _is_loopback(host: str) -> bool:
    if host == 'localhost':
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@app.get('/configuration')
def configuration():
    return {
        'version': jt.__version__,
        'configuration': {
            'JUTURNA_DRAIN_TIMEOUT': jt.meta.JUTURNA_DRAIN_TIMEOUT,
            'JUTURNA_MAX_QUEUE_SIZE': jt.meta.JUTURNA_MAX_QUEUE_SIZE,
            'JUTURNA_TELEMETRY_BATCH_SIZE': jt.meta.JUTURNA_TELEMETRY_BATCH_SIZE,  # noqa: E501
            'JUTURNA_THREAD_JOIN_TIMEOUT': jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT,
        },
    }


@app.get('/pipelines')
def pipelines():
    return PipelineManager().pipeline_list()


@app.post('/pipelines/new', response_model=SuccessfulResponse)
def new_pipeline(pipeline_config: PipelineConfig):
    created_pipeline_dto = PipelineManager().create_pipeline(pipeline_config)
    logger.info(f'created pipe with id: {created_pipeline_dto.pipeline_id}')

    return SuccessfulResponse(data=created_pipeline_dto)


@app.post('/pipelines/{pipeline_id}/warmup')
def warmup_pipeline(pipeline_id: str):
    PipelineManager().warmup_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/start')
def start_pipeline(pipeline_id: str):
    PipelineManager().start_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/deploy')
def deploy_pipeline(pipeline_config: PipelineConfig):
    created_pipeline_dto = PipelineManager().deploy_pipeline(pipeline_config)

    return PipelineManager().pipeline_status(created_pipeline_dto.pipeline_id)


@app.post('/pipelines/{pipeline_id}/stop')
def stop_pipeline(pipeline_id: str):
    PipelineManager().stop_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/delete', response_model=SuccessfulResponse)
def delete_pipeline(pipeline_id: str, wipe: bool = False):
    PipelineManager().delete_pipeline(pipeline_id, wipe)

    return SuccessfulResponse()


@app.get('/pipelines/{pipeline_id}/status')
def pipeline_status(pipeline_id: str):
    status = PipelineManager().pipeline_status(pipeline_id)

    return status


@app.get('/pipelines/{pipeline_id}/telemetry')
def pipeline_telemetry(pipeline_id: str):
    telemetry_data = PipelineManager().pipeline_telemetry(pipeline_id)

    return {'pipeline': pipeline_id, 'telemetry': telemetry_data}


def run(
    host: str,
    port: int,
    folder: str,
    log_config: str,
    dev: bool,
    allow_env: list[str] | None = None,
    auth: bool = True,
):
    if log_config:
        with open(log_config) as f:
            cfg = json.load(f)

        logging.config.dictConfig(cfg)

    logger.info('starting juturna service...')

    app.state.auth = auth
    app.state.token = os.environ.get(TOKEN_ENV_VAR) if auth else None

    if not auth:
        # without the token, any client that reaches the port, and any web
        # page open in a browser on this host (cross-site simple requests),
        # can deploy pipelines
        logger.warning(
            'authentication disabled: every client that can reach '
            f'{host}:{port} has full access to the service'
        )

        if os.environ.get(TOKEN_ENV_VAR):
            logger.warning(f'{TOKEN_ENV_VAR} is set but ignored')
    elif not app.state.token:
        app.state.token = secrets.token_urlsafe(32)

        # printed on the console only, never logged (logs may be shipped)
        print(
            f'{TOKEN_ENV_VAR} not set, generated service token: '
            f'{app.state.token}',
            file=sys.stderr,
        )

    if not _is_loopback(host):
        logger.warning(
            f'service bound to {host}, reachable from the network over plain '
            'HTTP: put it behind a TLS proxy'
        )

    if dev:
        enable_cross_origins(app)

        logger.info('development mode enabled')

    try:
        pathlib.Path(folder).mkdir(parents=True)
        logger.info(f'pipeline folder {folder} created')
    except FileExistsError:
        logger.info(f'pipeline folder {folder} exists, skipping...')

    PipelineManager().set_base_folder(folder)
    PipelineManager().set_allowed_env_vars(allow_env or list())

    logger.info(f'service address: {host}:{port}')

    uvicorn.run(
        'juturna.cli.commands._juturna_service:app',
        host=host,
        port=port,
    )
