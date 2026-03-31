import pathlib
import logging

import uvicorn

import juturna as jt

from fastapi import FastAPI

from juturna.components._pipeline_manager import PipelineManager
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import SuccessfulResponse
from juturna.cli.commands.exceptions import (
    register_pipeline_exception_handlers,
    register_generic_exception_handler,
)

app = FastAPI()
logger = logging.getLogger('jt.service')

##register exception handlers
register_pipeline_exception_handlers(app)
register_generic_exception_handler(app, logger)


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


def run(
    host: str,
    port: int,
    folder: str,
    log_level: str,
    log_format: str,
    log_file: str,
):
    jt.log.formatter(log_format)
    jt.log.jt_logger().setLevel(log_level)

    if log_file:
        _handler = logging.FileHandler(log_file)
        jt.log.add_handler(_handler)

    logger.info('starting juturna service...')

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
