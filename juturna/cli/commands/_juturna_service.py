import pathlib
import json
import logging
import logging.config

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import juturna as jt

from juturna.components._pipeline_manager import PipelineManager
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import SuccessfulResponse
from juturna.cli.commands.exceptions import (
    register_pipeline_exception_handlers,
    register_generic_exception_handler,
)

app = FastAPI()
logger = logging.getLogger('jt.service')

# register exception handlers
register_pipeline_exception_handlers(app)
register_generic_exception_handler(app, logger)


def enable_cross_origins(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


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


def run(host: str, port: int, folder: str, log_config: str, dev: bool):
    if log_config:
        with open(log_config) as f:
            cfg = json.load(f)

        logging.config.dictConfig(cfg)

    logger.info('starting juturna service...')

    if dev:
        enable_cross_origins(app)

        logger.info('development mode enabled')

    try:
        pathlib.Path(folder).mkdir(parents=True)
        logger.info(f'pipeline folder {folder} created')
    except FileExistsError:
        logger.info(f'pipeline folder {folder} exists, skipping...')

    PipelineManager().set_base_folder(folder)

    logger.info(f'service address: {host}:{port}')

    uvicorn.run(
        'juturna.cli.commands._juturna_service:app',
        host=host,
        port=port,
    )
