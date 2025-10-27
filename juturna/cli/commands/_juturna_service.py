import pathlib
import logging

import uvicorn
import fastapi
import pydantic

import juturna as jt

from juturna.components._pipeline_manager import PipelineManager


app = fastapi.FastAPI()
logger = logging.getLogger('jt.service')


class PipelineConfig(pydantic.BaseModel):
    version: str
    plugins: list
    pipeline: dict


@app.get('/pipelines')
def pipelines():
    return PipelineManager().pipeline_list()


@app.post('/pipelines/new')
def new_pipeline(pipeline_config: PipelineConfig):
    container = PipelineManager().create_pipeline(pipeline_config.model_dump())
    logger.info(f'created pipe, id {container["pipeline_id"]}')

    return container


@app.post('/pipelines/{pipeline_id}/warmup')
def warmup_pipeline(pipeline_id: str):
    PipelineManager().warmup_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/start')
def start_pipeline(pipeline_id: str):
    PipelineManager().start_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/stop')
def stop_pipeline(pipeline_id: str):
    PipelineManager().stop_pipeline(pipeline_id)

    return PipelineManager().pipeline_status(pipeline_id)


@app.post('/pipelines/{pipeline_id}/delete')
def delete_pipeline(pipeline_id: str, wipe: bool = False):
    del_status = PipelineManager().delete_pipeline(pipeline_id, wipe)

    return del_status


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
