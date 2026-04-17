import uuid
import sys
import gc
import threading
import shutil
import logging
import pathlib

from juturna.components import Pipeline
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import CreatedPipelineDto
from juturna.cli.commands.exceptions import (
    AlreadyWarmedupException,
    InvalidPipelineIdException,
    AlreadyRunningException,
    NotReadyException,
    NotRunningException,
)
from juturna.names import PipelineStatus


logger = logging.getLogger('jt.manager')


class PipelineManager:
    _instance = None
    _base_folder = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._pipelines = dict()

        return cls._instance

    def __len__(self):
        return len(self._pipelines)

    @classmethod
    def set_base_folder(cls, base_folder: str) -> str:
        if cls._base_folder is None:
            cls._base_folder = base_folder

        return cls()

    @property
    def base_folder(self) -> str:
        return self.__class__._base_folder

    def create_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> CreatedPipelineDto:
        pipeline_id = str(uuid.uuid4())

        pipeline_config.pipeline['id'] = pipeline_id
        pipeline_config.pipeline['folder'] = str(
            pathlib.Path(
                self.base_folder,
                f'{pipeline_config.pipeline["name"]}_{pipeline_id}',
            )
        )

        this_pipeline = Pipeline(pipeline_config.model_dump())

        self._pipelines[this_pipeline.pipe_id] = this_pipeline

        return CreatedPipelineDto(
            pipeline_id=this_pipeline.pipe_id,
            created_at=this_pipeline.created_at,
            status=this_pipeline.status['self'],
        )

    def warmup_pipeline(self, pipeline_id: str) -> None:
        if pipeline_id not in self._pipelines:
            raise InvalidPipelineIdException(pipeline_id)

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.READY:
            raise AlreadyWarmedupException(pipeline_id)

        self._pipelines[pipeline_id].warmup()

    def start_pipeline(self, pipeline_id: str) -> None:
        if pipeline_id not in self._pipelines:
            raise InvalidPipelineIdException(pipeline_id)

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.NEW:
            raise NotReadyException(pipeline_id)

        if (
            self._pipelines[pipeline_id].status['self']
            == PipelineStatus.RUNNING
        ):
            raise AlreadyRunningException(pipeline_id)

        self._pipelines[pipeline_id].start()

    def deploy_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> CreatedPipelineDto:
        created_pipe_dto = self.create_pipeline(pipeline_config)

        for operation in [self.warmup_pipeline, self.start_pipeline]:
            operation(created_pipe_dto.pipeline_id)

        return created_pipe_dto

    def stop_pipeline(self, pipeline_id: str) -> None:
        if pipeline_id not in self._pipelines:
            raise InvalidPipelineIdException(pipeline_id)

        if (
            self._pipelines[pipeline_id].status['self']
            != PipelineStatus.RUNNING
        ):
            raise NotRunningException(pipeline_id)

        self._pipelines[pipeline_id].stop()

    def delete_pipeline(self, pipeline_id: str, wipe_folder: bool) -> None:
        if pipeline_id not in self._pipelines:
            raise InvalidPipelineIdException(pipeline_id)

        sys.exc_info()

        self._pipelines[pipeline_id].destroy()
        _target_folder = self._pipelines[pipeline_id].pipe_path
        if _target_folder and wipe_folder:
            try:
                shutil.rmtree(_target_folder)
                logger.info(f'wiped pipeline folder {_target_folder}')
            except FileNotFoundError:
                logger.warning(f'pipeline folder {_target_folder} not found')

        del self._pipelines[pipeline_id]

        gc.collect()

    def pipeline_status(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            raise InvalidPipelineIdException(pipeline_id)

        logger.info(f'requested status for pipeline {pipeline_id}')
        logger.info(self._pipelines[pipeline_id].status)

        return self._pipelines[pipeline_id].status

    def pipeline_list(self) -> dict:
        return {
            'pipelines': [
                {p_id: self._pipelines[p_id].status for p_id in self._pipelines}
            ]
        }

    def cleanup(self):
        for _pipeline_id in list(self._pipelines.keys()):
            self._pipelines[_pipeline_id].stop()
            self._pipelines[_pipeline_id].destroy()

            del self._pipelines[_pipeline_id]
