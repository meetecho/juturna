# noqa: D101
"""Collector module for Exceptions raised when acting on Pipeline objects"""


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


class AlreadyWarmedupException(BasePipelineException):
    pass


class NotReadyException(BasePipelineException):
    pass


class AlreadyRunningException(BasePipelineException):
    pass


class NotRunningException(BasePipelineException):
    pass
