from enum import StrEnum
from enum import unique


@unique
class PipelineStatus(StrEnum):
    """
    Possible state values of a pipeline.

    - ``NEW``: a pipeline was instantiated, but its nodes are not built yet
    - ``READY``: nodes were instantiated and linked, the pipeline can start
    - ``RUNNING``: the pipeline is consuming, processing and sending data
    - ``STOPPED``: a previously running pipeline was stopped; it cannot be
      started again, only destroyed
    - ``DESTROYED``: the pipeline released its resources and is no longer
      usable
    """

    NEW = 'pipeline_created'
    READY = 'pipeline_ready'
    RUNNING = 'pipeline_running'
    STOPPED = 'pipeline_stopped'
    DESTROYED = 'pipeline_destroyed'
