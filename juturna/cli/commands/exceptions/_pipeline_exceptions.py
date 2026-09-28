# noqa: D101
"""
Collector module for exceptions raised when acting on Pipeline objects.

Illegal lifecycle transitions (warmup/start/stop) are validated and raised by
Pipeline itself (see juturna.components.exceptions): this module only keeps
exceptions specific to the manager/HTTP layer, i.e. concerns Pipeline has no
notion of (an unknown id in the registry, telemetry not configured).
"""

from juturna.components.exceptions import PipelineStateError
from juturna.components.exceptions import PipelineNotReadyError
from juturna.components.exceptions import PipelineNotRunningError
from juturna.components.exceptions import PipelineAlreadyRunningError
from juturna.components.exceptions import PipelineStoppedError
from juturna.components.exceptions import PipelineDestroyedError
from juturna.components.exceptions import PipelineBusyError


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
