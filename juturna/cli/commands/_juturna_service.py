import pathlib
import logging

import uvicorn

import juturna as jt

from fastapi import FastAPI

from juturna.components._pipeline_manager import PipelineManager
from juturna.models.api import PipelineConfig
from juturna.models.api import PipelineCreatedResponse
from juturna.models.api import SuccessfulResponse
from juturna.models.api import UnsuccessfulResponse
from juturna.utils.http_utils import raise_on_unsuccessful_response


app = FastAPI()
logger = logging.getLogger('jt.service')


@app.get('/pipelines')
def pipelines():
    return PipelineManager().pipeline_list()


@app.post('/pipelines/new', response_model=PipelineCreatedResponse)
def new_pipeline(pipeline_config: PipelineConfig):
    response = PipelineManager().create_pipeline(pipeline_config)
    if isinstance(response, UnsuccessfulResponse):
        raise_on_unsuccessful_response(response)

    logger.info(f'created pipe, id {response.pipeline_id}')

    return response


@app.post('/pipelines/{pipeline_id}/warmup')
def warmup_pipeline(pipeline_id: str):
    response = PipelineManager().warmup_pipeline(pipeline_id)
    if isinstance(response, UnsuccessfulResponse):
        raise_on_unsuccessful_response(response)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/start')
def start_pipeline(pipeline_id: str):
    response = PipelineManager().start_pipeline(pipeline_id)
    if isinstance(response, UnsuccessfulResponse):
        raise_on_unsuccessful_response(response)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/stop')
def stop_pipeline(pipeline_id: str):
    response = PipelineManager().stop_pipeline(pipeline_id)
    if isinstance(response, UnsuccessfulResponse):
        raise_on_unsuccessful_response(response)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/delete', response_model=SuccessfulResponse)
def delete_pipeline(pipeline_id: str, wipe: bool = False):
    response = PipelineManager().delete_pipeline(pipeline_id, wipe)
    if isinstance(response, UnsuccessfulResponse):
        raise_on_unsuccessful_response(response)

    return response


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
