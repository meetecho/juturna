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


class EnvVarNotAllowedException(Exception):
    def __init__(self, var_name: str, node_name: str):
        """
        Raise when a pipeline configuration references an environment
        variable the service does not allow

        Args:
            var_name (str): name of the environment variable
            node_name (str): node whose configuration references it

        """
        super().__init__(var_name, node_name)

        self.var_name = var_name
        self.node_name = node_name


__all__ = [
    'BasePipelineException',
    'InvalidPipelineIdException',
    'TelemetryNotEnabledException',
    'PipelineStateError',
    'PipelineNotReadyError',
    'PipelineNotRunningError',
    'PipelineAlreadyRunningError',
    'PipelineStoppedError',
    'PipelineDestroyedError',
    'PipelineBusyError',
]
