import uuid
import sys
import gc
import threading
import shutil
import logging
import pathlib

from juturna.components import Pipeline
from juturna.names import ServiceStatus
from juturna.names import PipelineStatus


logger = logging.getLogger('jt.manager')

_INVALID_ID_MSG = {
    'status': ServiceStatus.REQUEST_KO,
    'reason': ServiceStatus.INVALID_ID,
}


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

    def create_pipeline(self, pipeline_config: dict) -> dict:
        pipeline_id = str(uuid.uuid4())

        pipeline_config['pipeline']['id'] = pipeline_id
        pipeline_config['pipeline']['folder'] = str(
            pathlib.Path(
                self.base_folder,
                f'{pipeline_config["pipeline"]["name"]}_{pipeline_id}',
            )
        )

        this_pipeline = Pipeline(pipeline_config)

        self._pipelines[this_pipeline.pipe_id] = this_pipeline

        pipeline_container = {
            'pipeline_id': this_pipeline.pipe_id,
            'created_at': this_pipeline.created_at,
            'status': this_pipeline.status['self'],
        }

        return pipeline_container

    def warmup_pipeline(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_MSG

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.READY:
            return {
                'status': ServiceStatus.REQUEST_KO,
                'reason': ServiceStatus.ALREADY_WARMEDUP,
            }

        self._pipelines[pipeline_id].warmup()

        return {'status': ServiceStatus.REQUEST_OK}

    def start_pipeline(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_MSG

        if self._pipelines[pipeline_id].status['self'] == PipelineStatus.NEW:
            return {
                'status': ServiceStatus.REQUEST_KO,
                'reason': ServiceStatus.NOT_READY,
            }

        if (
            self._pipelines[pipeline_id].status['self']
            == PipelineStatus.RUNNING
        ):
            return {
                'status': ServiceStatus.REQUEST_KO,
                'reason': ServiceStatus.ALREADY_RUNNING,
            }

        self._pipelines[pipeline_id].start()

        return {'status': ServiceStatus.REQUEST_OK}

    def stop_pipeline(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_MSG

        if (
            self._pipelines[pipeline_id].status['self']
            != PipelineStatus.RUNNING
        ):
            return {
                'status': ServiceStatus.REQUEST_KO,
                'reason': ServiceStatus.NOT_RUNNING,
            }

        self._pipelines[pipeline_id].stop()
        self._pipelines[pipeline_id].status['self'] = PipelineStatus.READY

        return {'status': ServiceStatus.REQUEST_OK}

    def delete_pipeline(self, pipeline_id: str, wipe_folder: bool):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_MSG

        sys.exc_info()

        self._pipelines[pipeline_id].destroy()

        if wipe_folder:
            shutil.rmtree(self._pipelines[pipeline_id].pipe_folder)

        del self._pipelines[pipeline_id]

        gc.collect()

        return {'status': ServiceStatus.REQUEST_OK}

    def pipeline_status(self, pipeline_id: str):
        if pipeline_id not in self._pipelines:
            return _INVALID_ID_MSG

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
