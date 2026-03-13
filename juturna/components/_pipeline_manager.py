import uuid
import sys
import gc
import threading
import shutil
import logging
import pathlib

from juturna.components import Pipeline
from juturna.models.api import PipelineConfig
from juturna.models.api import PipelineCreatedResponse
from juturna.models.api import SuccessfulResponse
from juturna.models.api import UnsuccessfulResponse
from juturna.names import ServiceFailureReason
from juturna.names import PipelineStatus


logger = logging.getLogger('jt.manager')

_INVALID_ID_RESPONSE = UnsuccessfulResponse(
    reason=ServiceFailureReason.INVALID_ID
)


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
    ) -> PipelineCreatedResponse | UnsuccessfulResponse:
        pipeline_id = str(uuid.uuid4())

        try:
            pipeline_config.pipeline['id'] = pipeline_id
            pipeline_config.pipeline['folder'] = str(
                pathlib.Path(
                    self.base_folder,
                    f'{pipeline_config.pipeline["name"]}_{pipeline_id}',
                )
            )

            this_pipeline = Pipeline(pipeline_config.model_dump())

            self._pipelines[this_pipeline.pipe_id] = this_pipeline

        except Exception as e:
            logger.exception('pipeline exception upon creation')
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.INTERNAL_ERROR, detail=f'{e}'
            )

        return PipelineCreatedResponse(
            pipeline_id=this_pipeline.pipe_id,
            created_at=this_pipeline.created_at,
            status=this_pipeline.status['self'],
        )

    def warmup_pipeline(
        self, pipeline_id: str
    ) -> SuccessfulResponse | UnsuccessfulResponse:
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_RESPONSE

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.READY:
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.ALREADY_WARMEDUP
            )

        try:
            self._pipelines[pipeline_id].warmup()
        except Exception as e:
            logger.exception('pipeline exception on warmup')
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.INTERNAL_ERROR, detail=f'{e}'
            )

        return SuccessfulResponse

    def start_pipeline(
        self, pipeline_id: str
    ) -> SuccessfulResponse | UnsuccessfulResponse:
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_RESPONSE

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.NEW:
            return UnsuccessfulResponse(reason=ServiceFailureReason.NOT_READY)

        if (
            self._pipelines[pipeline_id].status['self']
            == PipelineStatus.RUNNING
        ):
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.ALREADY_RUNNING
            )

        try:
            self._pipelines[pipeline_id].start()
        except Exception as e:
            logger.exception('pipeline exception on start')
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.INTERNAL_ERROR, detail=f'{e}'
            )

        return SuccessfulResponse

    def deploy_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> PipelineCreatedResponse | UnsuccessfulResponse:
        created_pipe_response = self.create_pipeline(pipeline_config)
        if isinstance(created_pipe_response, UnsuccessfulResponse):
            return created_pipe_response

        for operation in [self.warmup_pipeline, self.start_pipeline]:
            response = operation(created_pipe_response.pipeline_id)
            if isinstance(response, UnsuccessfulResponse):
                return response

        return created_pipe_response

    def stop_pipeline(
        self, pipeline_id: str
    ) -> SuccessfulResponse | UnsuccessfulResponse:
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_RESPONSE

        if (
            self._pipelines[pipeline_id].status['self']
            != PipelineStatus.RUNNING
        ):
            return UnsuccessfulResponse(reason=ServiceFailureReason.NOT_RUNNING)

        try:
            self._pipelines[pipeline_id].stop()
            self._pipelines[pipeline_id].status['self'] = PipelineStatus.READY
        except Exception as e:
            logger.exception('pipeline exception on stop')
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.INTERNAL_ERROR, detail=f'{e}'
            )

        return SuccessfulResponse

    def delete_pipeline(
        self, pipeline_id: str, wipe_folder: bool
    ) -> SuccessfulResponse | UnsuccessfulResponse:
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_RESPONSE

        sys.exc_info()

        try:
            self._pipelines[pipeline_id].destroy()

            _target_folder = self._pipelines[pipeline_id].pipe_path

            if _target_folder and wipe_folder:
                try:
                    shutil.rmtree(_target_folder)

                    logger.info(f'wiped pipeline folder {_target_folder}')
                except FileNotFoundError:
                    logger.warning(
                        f'pipeline folder {_target_folder} not found'
                    )

            del self._pipelines[pipeline_id]

            gc.collect()

        except Exception as e:
            logger.exception('pipeline exception on deletion')
            return UnsuccessfulResponse(
                reason=ServiceFailureReason.INTERNAL_ERROR, detail=f'{e}'
            )

        return SuccessfulResponse

    def pipeline_status(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_RESPONSE

        logger.info('requested status')
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
