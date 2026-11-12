import os
import sys
import pathlib
import json
import secrets
import ipaddress
import logging
import logging.config

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from typing import Any

import uvicorn

from fastapi import Body
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

import juturna as jt

from juturna.cli.commands._node_catalogue import node_catalogue
from juturna.cli.commands._pipeline_manager import PipelineManager
from juturna.cli.commands.validate import validate_configuration
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import SuccessfulResponse
from juturna.cli.commands.exceptions import (
    register_pipeline_exception_handlers,
    register_generic_exception_handler,
)

TOKEN_ENV_VAR = 'JUTURNA_SERVICE_TOKEN'

# the largest request body the service reads: pipeline configurations are
# small, and the body is held in memory while it is parsed
MAX_BODY_BYTES = 1024 * 1024

_bearer = HTTPBearer(auto_error=False)


def _token_problem(state: Any, token: str | None) -> tuple[int, str] | None:
    """
    Compare a bearer token with the one of the service. Return ``None`` when
    the request can go on, or the status code and the reason to answer.
    """
    if not getattr(state, 'auth', True):
        return None

    expected = getattr(state, 'token', None) or os.environ.get(TOKEN_ENV_VAR)

    if not expected:
        return 503, 'service token not configured'

    if token is None or not secrets.compare_digest(
        token.encode(), expected.encode()
    ):
        return 401, 'missing or invalid service token'

    return None


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

    The same check runs earlier, in ``_Guard``, for every path and before
    the body is read. This dependency stays so that the routes declare the
    credential they need in the OpenAPI document.
    """
    problem = _token_problem(
        request.app.state,
        None if credentials is None else credentials.credentials,
    )

    if problem is not None:
        raise _auth_error(*problem)


def _auth_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={'WWW-Authenticate': 'Bearer'} if status_code == 401 else None,
    )


class _Guard:
    """
    Check every request before any of it is handled: the token first, then
    the size of the body.

    A route dependency runs after the body is read and parsed, so without
    this an anonymous client could make the service read a body of any size,
    and learn from the answer (422, not 401) how its content was understood.
    It also covers the paths that have no dependency: ``/docs``, ``/redoc``
    and ``/openapi.json``.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)

            return

        state = scope['app'].state
        headers = {
            name.decode('latin-1').lower(): value.decode('latin-1')
            for name, value in scope['headers']
        }

        problem = _token_problem(
            state, _bearer_token(headers.get('authorization'))
        )

        if problem is None:
            problem = _length_problem(state, headers.get('content-length'))

        if problem is not None:
            status_code, detail = problem
            response = JSONResponse(
                status_code=status_code,
                content={'detail': detail},
                headers=(
                    {'WWW-Authenticate': 'Bearer'}
                    if status_code == 401
                    else None
                ),
            )

            await response(scope, receive, send)

            return

        await self.app(scope, _capped(receive, _max_body(state)), send)


def _bearer_token(authorization: str | None) -> str | None:
    scheme, _, token = (authorization or '').partition(' ')

    if scheme.lower() != 'bearer' or not token.strip():
        return None

    return token.strip()


def _max_body(state: Any) -> int:
    return getattr(state, 'max_body_bytes', None) or MAX_BODY_BYTES


def _length_problem(
    state: Any, content_length: str | None
) -> tuple[int, str] | None:
    if content_length is None:
        return None

    if not content_length.isdigit():
        return 400, 'invalid Content-Length'

    if int(content_length) > _max_body(state):
        return 413, f'request body larger than {_max_body(state)} bytes'

    return None


def _capped(receive, limit: int):
    """
    Count the body as it arrives: a client that sends it in chunks declares
    no length, and one that declares a length can still send more.
    """
    received = 0

    async def capped_receive():
        nonlocal received

        message = await receive()

        if message['type'] == 'http.request':
            received += len(message.get('body', b''))

            if received > limit:
                raise HTTPException(
                    status_code=413,
                    detail=f'request body larger than {limit} bytes',
                )

        return message

    return capped_receive


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield

    # pipelines left running would keep their nodes, threads and files
    # after the service is gone
    PipelineManager().cleanup()


app = FastAPI(dependencies=[Depends(require_token)], lifespan=_lifespan)
logger = logging.getLogger('jt.service')

# added first, so it stays inside the CORS middleware of the development
# mode: preflight requests carry no token, and the answers of the guard
# still get the CORS headers
app.add_middleware(_Guard)

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
            'JUTURNA_MAX_QUEUE_SIZE': jt.meta.JUTURNA_MAX_QUEUE_SIZE,
            'JUTURNA_TELEMETRY_BATCH_SIZE': jt.meta.JUTURNA_TELEMETRY_BATCH_SIZE,  # noqa: E501
            'JUTURNA_THREAD_JOIN_TIMEOUT': jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT,
        },
    }


@app.get('/nodes')
def nodes():
    """The node types installed on the service, with their defaults"""
    return {'nodes': node_catalogue()}


@app.get('/pipelines')
def pipelines():
    return PipelineManager().pipeline_list()


@app.post('/pipelines/validate')
def validate_pipeline(configuration: Annotated[Any, Body()]):
    """
    Check a configuration as ``juturna validate`` does, without creating
    anything. The answer is always the report, valid or not: any JSON
    document is accepted, so that the report can say what is wrong with it.
    """
    return validate_configuration(
        configuration, env_var_names=PipelineManager().env_var_names()
    ).to_dict()


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


@app.get('/pipelines/{pipeline_id}/config')
def pipeline_config(pipeline_id: str):
    return PipelineManager().pipeline_config(pipeline_id)


@app.get('/pipelines/{pipeline_id}/logs')
def pipeline_logs(pipeline_id: str, since: float | None = None):
    logs = PipelineManager().pipeline_logs(pipeline_id, since)

    return {'pipeline': pipeline_id, 'logs': logs}


@app.get('/pipelines/{pipeline_id}/files')
def pipeline_files(pipeline_id: str):
    files = PipelineManager().pipeline_files(pipeline_id)

    return {'pipeline': pipeline_id, 'files': files}


@app.get('/pipelines/{pipeline_id}/files/{file_path:path}')
def pipeline_file(pipeline_id: str, file_path: str):
    path = PipelineManager().pipeline_file(pipeline_id, file_path)

    # always a download, never a page: a pipeline can write any content, and
    # a browser must not render it as coming from the service
    return FileResponse(
        path,
        media_type='application/octet-stream',
        filename=path.name,
        headers={'X-Content-Type-Options': 'nosniff'},
    )


@app.get('/pipelines/{pipeline_id}/telemetry')
def pipeline_telemetry(pipeline_id: str):
    telemetry_data = PipelineManager().pipeline_telemetry(pipeline_id)

    return {'pipeline': pipeline_id, 'telemetry': telemetry_data}


def _check_env_file(env_file: str):
    """
    Read the environment file once, so that a file that cannot be parsed
    stops the service at startup, and warn when other users can read it.
    """
    try:
        names = jt.utils.jt_utils.read_env_file(env_file)
    except (OSError, ValueError) as error:
        # the message has the line number, never the content of the line
        sys.exit(f'cannot use the environment file: {error}')

    # names only: the values are secrets
    logger.info(
        f'environment file {env_file}: {len(names)} variables available to '
        'pipeline configurations'
    )

    if os.name == 'posix' and os.stat(env_file).st_mode & 0o077:
        logger.warning(
            f'environment file {env_file} can be read by other users: '
            'restrict it with chmod 600'
        )


def run(
    host: str,
    port: int,
    folder: str,
    log_config: str,
    dev: bool,
    allow_env: list[str] | None = None,
    auth: bool = True,
    env_file: str | None = None,
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
    PipelineManager().set_env_file(env_file)

    if env_file:
        _check_env_file(env_file)

    if '*' in (allow_env or list()):
        logger.warning(
            'every variable of the service environment can be read by '
            'pipeline configurations (--allow-env "*")'
        )

    logger.info(f'service address: {host}:{port}')

    uvicorn.run(
        'juturna.cli.commands._juturna_service:app',
        host=host,
        port=port,
    )
