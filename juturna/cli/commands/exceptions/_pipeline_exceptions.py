# noqa: D101
"""
Collector module for exceptions raised when acting on Pipeline objects.

Illegal lifecycle transitions (warmup/start/stop) are validated and raised by
Pipeline itself (see juturna.components.exceptions): this module only keeps
exceptions specific to the manager/HTTP layer, i.e. concerns Pipeline has no
notion of (an unknown id in the registry, telemetry not configured).
"""

from juturna.components.exceptions import (
    PipelineStateError,
    PipelineAlreadyRunningError,
    PipelineNotReadyError,
    PipelineNotRunningError,
    PipelineStoppedError,
    PipelineDestroyedError,
    PipelineBusyError,
    EnvVarNotAllowedError,
)


class BasePipelineException(Exception):
    def __init__(self, pipeline_id: str):
        """
        Raise a Pipeline Exception

        Args:
            pipeline_id (str): pipeline id

        """
        self.pipeline_id = pipeline_id


class InvalidPipelineIdException(BasePipelineException):
    pass


class TelemetryNotEnabledException(BasePipelineException):
    pass


class PipelineOperationException(BasePipelineException):
    """
    A lifecycle operation failed because of the pipeline content: a node
    type the service does not have, a node that cannot be built, warmed up
    or started. It is the client's configuration that has to change.
    """

    def __init__(
        self,
        pipeline_id: str,
        operation: str,
        error: Exception,
    ):
        """
        Parameters
        ----------
        pipeline_id : str
            The pipeline the operation was called on.
        operation : str
            The lifecycle operation: ``warmup`` or ``start``.
        error : Exception
            What the pipeline raised. Its ``node_name``, when the pipeline
            recorded one, is the node that failed.

        """
        super().__init__(pipeline_id)

        self.operation = operation
        self.node_name: str | None = getattr(error, 'node_name', None)
        self.reason = f'{type(error).__name__}: {error}'

        where = (
            f'node {self.node_name}'
            if self.node_name
            else f'pipeline {pipeline_id}'
        )
        self.message = f'{operation} failed on {where}: {self.reason}'

    def __str__(self) -> str:
        return self.message


class PipelineFileNotFoundException(BasePipelineException):
    def __init__(self, pipeline_id: str, path: str):
        """
        Parameters
        ----------
        pipeline_id : str
            The pipeline whose folder was read.
        path : str
            The path asked for, relative to the pipeline folder.

        """
        super().__init__(pipeline_id)

        self.path = path


# raised by the pipeline as well when a node is built: one name, one handler
EnvVarNotAllowedException = EnvVarNotAllowedError


__all__ = [
    'BasePipelineException',
    'InvalidPipelineIdException',
    'TelemetryNotEnabledException',
    'PipelineOperationException',
    'PipelineFileNotFoundException',
    'EnvVarNotAllowedException',
    'PipelineStateError',
    'PipelineNotReadyError',
    'PipelineNotRunningError',
    'PipelineAlreadyRunningError',
    'PipelineStoppedError',
    'PipelineDestroyedError',
    'PipelineBusyError',
]
