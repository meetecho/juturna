import collections
import copy
import uuid
import gc
import threading
import shutil
import logging
import pathlib

from juturna.components import Pipeline
from juturna.names import PipelineStatus
from juturna.utils import jt_utils
from juturna.cli.commands.models.api import PipelineConfig
from juturna.cli.commands.models.api import CreatedPipelineDto
from juturna.cli.commands.exceptions import (
    InvalidPipelineIdException,
    TelemetryNotEnabledException,
    PipelineOperationException,
    PipelineFileNotFoundException,
    PipelineStateError,
    EnvVarNotAllowedException,
)


logger = logging.getLogger('jt.manager')

# how many log records the service keeps for each pipeline
LOG_BUFFER_SIZE = 1000


class _LogBuffer(logging.Handler):
    """
    Keep the last records of a pipeline logger in memory, for the clients of
    the service. The nodes log under the pipeline logger, so their records
    are kept as well.
    """

    def __init__(self, size: int = LOG_BUFFER_SIZE):
        super().__init__()

        self._records = collections.deque(maxlen=size)
        self._formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                'ts': record.created,
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
            }

            if record.exc_info:
                entry['exception'] = self._formatter.formatException(
                    record.exc_info
                )

            # appending to a deque is atomic, no lock is needed
            self._records.append(entry)
        except Exception:
            self.handleError(record)

    def records(self, since: float | None = None) -> list[dict]:
        records = list(self._records)

        if since is None:
            return records

        return [r for r in records if r['ts'] > since]


class PipelineManager:
    _instance = None
    _base_folder = None
    _allowed_env_vars = frozenset()
    _env_file = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # compared with None: the manager has a length, so an empty one is
        # false, and would be replaced by a new instance
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pipelines = dict()
                    cls._instance._log_buffers = dict()

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

    @classmethod
    def set_env_file(cls, env_file: str | None):
        """
        Set the file the variables of the pipelines are read from. It is
        read again for every new pipeline, so that it can change while the
        service runs.
        """
        cls._env_file = env_file

        return cls()

    @property
    def base_folder(self) -> str:
        return self.__class__._base_folder

    def _read_env_file(self) -> dict[str, str] | None:
        if self._env_file is None:
            return None

        return jt_utils.read_env_file(self._env_file)

    def env_var_names(self) -> set[str]:
        """Names of the variables of the environment file, if there is one"""
        return set(self._read_env_file() or dict())

    def create_pipeline(
        self, pipeline_config: PipelineConfig
    ) -> CreatedPipelineDto:
        # the name becomes the pipeline folder under the base folder
        jt_utils.check_name(pipeline_config.pipeline.get('name'), 'pipeline')

        pipeline_id = str(uuid.uuid4())

        pipeline_config.pipeline['id'] = pipeline_id
        pipeline_config.pipeline['folder'] = str(
            pathlib.Path(
                self.base_folder,
                f'{pipeline_config.pipeline["name"]}_{pipeline_id}',
            )
        )

        # configurations come from service clients: they may only resolve the
        # environment variables the operator allowed, or they could route any
        # service secret into a node that sends it out. The pipeline refuses
        # the others here, and again when it builds its nodes. The variables
        # of the environment file are handed to the pipeline, and never
        # enter the environment of the service
        this_pipeline = Pipeline(
            pipeline_config.model_dump(),
            allowed_env_vars=self._allowed_env_vars,
            env_vars=self._read_env_file(),
        )

        log_buffer = _LogBuffer()
        this_pipeline._logger.addHandler(log_buffer)

        with self._registry_lock:
            self._pipelines[this_pipeline.pipe_id] = this_pipeline
            self._log_buffers[this_pipeline.pipe_id] = log_buffer

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
        self._run(pipeline_id, 'warmup')

    def start_pipeline(self, pipeline_id: str) -> None:
        self._run(pipeline_id, 'start')

    def _run(self, pipeline_id: str, operation: str) -> None:
        """
        Warm up or start a pipeline. A call the pipeline status does not
        allow, or a variable the service does not allow, keeps its own error
        and answer. Anything else comes from the content of the pipeline (a
        node type that is not installed, a node that cannot be built or
        started): it is reported to the client with the node and the reason,
        where it used to be an anonymous 500.
        """
        pipeline = self._get(pipeline_id)

        try:
            getattr(pipeline, operation)()
        except (PipelineStateError, EnvVarNotAllowedException):
            raise
        except Exception as error:
            logger.exception(f'{operation} of pipeline {pipeline_id} failed')

            raise PipelineOperationException(
                pipeline_id, operation, error
            ) from error

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

        self._drop_log_buffer(pipeline)

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

        self._drop_log_buffer(pipeline)

        gc.collect()

    def _drop_log_buffer(self, pipeline: Pipeline):
        with self._registry_lock:
            log_buffer = self._log_buffers.pop(pipeline.pipe_id, None)

        if log_buffer is not None:
            pipeline._logger.removeHandler(log_buffer)

    def pipeline_status(self, pipeline_id: str):
        pipeline = self._get(pipeline_id)

        # clients poll the status: not worth a line at INFO each time
        logger.debug(f'requested status for pipeline {pipeline_id}')

        return pipeline.status

    def pipeline_config(self, pipeline_id: str) -> dict:
        """
        The configuration the pipeline was created with, id and folder
        included.
        """
        return copy.deepcopy(self._get(pipeline_id)._raw_config)

    def pipeline_logs(
        self, pipeline_id: str, since: float | None = None
    ) -> list[dict]:
        """
        The last records of the pipeline logger and of its nodes, oldest
        first: those after ``since`` (a unix time), or all the ones kept.
        Only the records that pass the level of the loggers are there.
        Pipelines with the same name share a logger, so each one also gets
        the records of the others.
        """
        self._get(pipeline_id)

        with self._registry_lock:
            log_buffer = self._log_buffers.get(pipeline_id)

        return list() if log_buffer is None else log_buffer.records(since)

    def pipeline_files(self, pipeline_id: str) -> list[dict]:
        """
        The files in the pipeline folder, by path. A link that leads out of
        the folder is not listed.
        """
        root = self._folder(pipeline_id)
        files = list()

        if root is None:
            return files

        for path in sorted(root.rglob('*')):
            try:
                if not path.is_file() or not self._inside(path, root):
                    continue

                stat = path.stat()
            except OSError:
                # removed meanwhile, or not readable
                continue

            files.append(
                {
                    'path': path.relative_to(root).as_posix(),
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                }
            )

        return files

    def pipeline_file(self, pipeline_id: str, file_path: str) -> pathlib.Path:
        """
        The location of a file of the pipeline folder, given its path in the
        folder. A path that is absolute, goes through ``..`` or follows a
        link out of the folder is answered like a file that does not exist.
        """
        root = self._folder(pipeline_id)
        missing = PipelineFileNotFoundException(pipeline_id, file_path)
        relative = pathlib.PurePosixPath(file_path)

        if (
            root is None
            or not file_path
            or '\\' in file_path
            or relative.is_absolute()
            or '..' in relative.parts
        ):
            raise missing

        path = root.joinpath(*relative.parts)

        try:
            if not path.is_file() or not self._inside(path, root):
                raise missing
        except OSError:
            raise missing from None

        return path.resolve()

    def _folder(self, pipeline_id: str) -> pathlib.Path | None:
        folder = pathlib.Path(self._get(pipeline_id).pipe_path)

        # created by warmup: a new pipeline has no files yet
        return folder.resolve() if folder.is_dir() else None

    @staticmethod
    def _inside(path: pathlib.Path, root: pathlib.Path) -> bool:
        return path.resolve().is_relative_to(root)

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
            self._drop_log_buffer(pipeline)

            try:
                if pipeline.status['self'] == PipelineStatus.RUNNING:
                    pipeline.kill()

                pipeline.destroy()
            except Exception:
                logger.exception(f'cannot release pipeline {pipeline_id}')
