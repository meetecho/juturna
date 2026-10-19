import uuid
import gc
import threading
import shutil
import logging
import pathlib

from juturna.components import Pipeline
from juturna.names import PipelineStatus
from juturna.meta import JUTURNA_ENV_VAR_PREFIX
from juturna.utils import jt_utils
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import CreatedPipelineDto
from juturna.cli.commands.exceptions import (
    InvalidPipelineIdException,
    TelemetryNotEnabledException,
    EnvVarNotAllowedException,
)


logger = logging.getLogger('jt.manager')


class PipelineManager:
    _instance = None
    _base_folder = None
    _allowed_env_vars = frozenset()
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._pipelines = dict()

                    # the service calls the manager from its thread pool: the
                    # registry is only read and changed under this lock, and
                    # the pipelines guard their own lifecycle
                    cls._instance._registry_lock = threading.Lock()

        return cls._instance

    def __len__(self):
        with self._registry_lock:
            return len(self._pipelines)

    @classmethod
    def set_base_folder(cls, base_folder: str) -> str:
        if cls._base_folder is None:
            cls._base_folder = base_folder

        return cls()

    @classmethod
    def set_allowed_env_vars(cls, names: list[str]):
        cls._allowed_env_vars = frozenset(names)

        return cls()

    @property
    def base_folder(self) -> str:
        return self.__class__._base_folder

    def _check_env_vars(self, pipeline: dict):
        # configurations come from service clients: they may only resolve the
        # environment variables the operator allowed, or they could route any
        # service secret into a node that sends it out
        for node in pipeline.get('nodes') or list():
            configuration = node.get('configuration') or dict()

            for value in configuration.values():
                if not (
                    isinstance(value, str)
                    and value.startswith(JUTURNA_ENV_VAR_PREFIX)
                ):
                    continue

                var_name = value[len(JUTURNA_ENV_VAR_PREFIX) :]

                if var_name not in self._allowed_env_vars:
                    raise EnvVarNotAllowedException(var_name, node.get('name'))

    def create_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> CreatedPipelineDto:
        # the name becomes the pipeline folder under the base folder
        jt_utils.check_name(pipeline_config.pipeline.get('name'), 'pipeline')
        self._check_env_vars(pipeline_config.pipeline)

        pipeline_id = str(uuid.uuid4())

        pipeline_config.pipeline['id'] = pipeline_id
        pipeline_config.pipeline['folder'] = str(
            pathlib.Path(
                self.base_folder,
                f'{pipeline_config.pipeline["name"]}_{pipeline_id}',
            )
        )

        this_pipeline = Pipeline(pipeline_config.model_dump())

        with self._registry_lock:
            self._pipelines[this_pipeline.pipe_id] = this_pipeline

        return CreatedPipelineDto(
            pipeline_id=this_pipeline.pipe_id,
            created_at=this_pipeline.created_at,
            status=this_pipeline.status['self'],
        )

    def _get(self, pipeline_id: str) -> Pipeline:
        with self._registry_lock:
            try:
                return self._pipelines[pipeline_id]
            except KeyError:
                raise InvalidPipelineIdException(pipeline_id) from None

    def warmup_pipeline(self, pipeline_id: str) -> None:
        self._get(pipeline_id).warmup()

    def start_pipeline(self, pipeline_id: str) -> None:
        self._get(pipeline_id).start()

    def deploy_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> CreatedPipelineDto:
        created_pipe_dto = self.create_pipeline(pipeline_config)

        try:
            for operation in [self.warmup_pipeline, self.start_pipeline]:
                operation(created_pipe_dto.pipeline_id)
        except BaseException:
            # the client never gets the id of a failed deploy, so nobody could
            # delete it: drop it with its folder
            self._discard(created_pipe_dto.pipeline_id)

            raise

        return created_pipe_dto

    def _discard(self, pipeline_id: str):
        with self._registry_lock:
            pipeline = self._pipelines.pop(pipeline_id, None)

        if pipeline is None:
            return

        try:
            pipeline.destroy()
        except Exception:
            logger.exception(f'cannot destroy pipeline {pipeline_id}')

        shutil.rmtree(pipeline.pipe_path, ignore_errors=True)

    def stop_pipeline(self, pipeline_id: str) -> None:
        self._get(pipeline_id).stop()

    def delete_pipeline(self, pipeline_id: str, wipe_folder: bool) -> None:
        pipeline = self._get(pipeline_id)

        # a pipeline that cannot be destroyed (busy, failing node) stays
        # registered, so the client can retry
        pipeline.destroy()

        _target_folder = pipeline.pipe_path
        if _target_folder and wipe_folder:
            try:
                shutil.rmtree(_target_folder)
                logger.info(f'wiped pipeline folder {_target_folder}')
            except FileNotFoundError:
                logger.warning(f'pipeline folder {_target_folder} not found')

        with self._registry_lock:
            self._pipelines.pop(pipeline_id, None)

        gc.collect()

    def pipeline_status(self, pipeline_id: str):
        pipeline = self._get(pipeline_id)

        logger.info(f'requested status for pipeline {pipeline_id}')
        logger.info(pipeline.status)

        return pipeline.status

    def pipeline_telemetry(self, pipeline_id: str):
        pipeline = self._get(pipeline_id)

        if not pipeline._telemetry:
            raise TelemetryNotEnabledException(pipeline_id)

        return pipeline._telemetry_manager.records()

    def pipeline_list(self) -> dict:
        with self._registry_lock:
            pipelines = dict(self._pipelines)

        return {
            'pipelines': [
                {p_id: pipeline.status for p_id, pipeline in pipelines.items()}
            ]
        }

    def cleanup(self):
        """
        Release every pipeline, as the service does when it shuts down.

        Running pipelines are killed rather than stopped, so a node stuck in
        update() cannot hold the shutdown. A pipeline that fails is logged and
        the others are still released.
        """
        with self._registry_lock:
            pipelines = dict(self._pipelines)
            self._pipelines.clear()

        for pipeline_id, pipeline in pipelines.items():
            try:
                if pipeline.status['self'] == PipelineStatus.RUNNING:
                    pipeline.kill()

                pipeline.destroy()
            except Exception:
                logger.exception(f'cannot release pipeline {pipeline_id}')
