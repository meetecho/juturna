from pydantic import BaseModel
from juturna.names import PipelineStatus


class CreatedPipelineDto(BaseModel):
    """container class for pipeline creation data"""

    pipeline_id: str
    created_at: float
    status: PipelineStatus
