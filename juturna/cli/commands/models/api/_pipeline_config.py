from pydantic import BaseModel


class PipelineConfig(BaseModel):
    """model for the json configuration given to HTTP endpoints"""

    version: str
    pipeline: dict
