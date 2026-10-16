from pydantic import BaseModel
from pydantic import field_validator

from juturna.utils import jt_utils


class PipelineConfig(BaseModel):
    """model for the json configuration given to HTTP endpoints"""

    version: str
    pipeline: dict

    @field_validator('pipeline')
    @classmethod
    def _check_names(cls, pipeline: dict) -> dict:
        """
        Reject pipeline, node and telemetry file names that are not plain file
        names, since they become paths under the service base folder.
        """
        jt_utils.check_name(pipeline.get('name'), 'pipeline')

        for node in pipeline.get('nodes', []):
            name = node.get('name') if isinstance(node, dict) else None
            jt_utils.check_name(name, 'node')

        if telemetry := pipeline.get('telemetry'):
            jt_utils.check_name(telemetry, 'telemetry file')

        return pipeline
