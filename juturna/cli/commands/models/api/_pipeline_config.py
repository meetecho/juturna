from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator

from juturna.components._pipeline import check_links
from juturna.telemetry import check_pipeline_telemetry
from juturna.transport import get_transport
from juturna.utils import jt_utils


def _check_list_of_dicts(pipeline: dict, key: str, fields: tuple[str, ...]):
    entries = pipeline.get(key)

    if not isinstance(entries, list):
        raise ValueError(f'pipeline "{key}" must be a list')

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f'every entry of "{key}" must be an object')

        for field in fields:
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValueError(f'every entry of "{key}" needs a "{field}"')


class PipelineConfig(BaseModel):
    """model for the json configuration given to HTTP endpoints"""

    # other top-level keys (plugins) are kept, so that a configuration read
    # back from the service is the one that was sent
    model_config = ConfigDict(extra='allow')

    version: str
    pipeline: dict

    @field_validator('version')
    @classmethod
    def _check_version(cls, version: str) -> str:
        if not version.strip():
            raise ValueError('"version" cannot be empty')

        return version

    @field_validator('pipeline')
    @classmethod
    def _check_pipeline(cls, pipeline: dict) -> dict:
        """
        Reject a pipeline the service could not build, with a 422 instead of
        an error at warmup: the nodes and links must be lists of objects with
        their keys, there must be at least one node, every link must join
        two nodes of the pipeline (once), a warped node needs its
        ``warp_configuration``, and the transport and telemetry must be ones
        the registries accept. Pipeline and node names, and the telemetry
        file name, must be plain file names, since they become paths under
        the service base folder.

        Node types are not resolved here: that imports the node packages. A
        type the service does not have is reported when the pipeline is
        warmed up, or by ``POST /pipelines/validate``.
        """
        jt_utils.check_name(pipeline.get('name'), 'pipeline')

        _check_list_of_dicts(pipeline, 'nodes', ('type',))
        _check_list_of_dicts(pipeline, 'links', ('from', 'to'))

        if not pipeline['nodes']:
            raise ValueError('pipeline "nodes" cannot be empty')

        names = set()

        for node in pipeline['nodes']:
            jt_utils.check_name(node.get('name'), 'node')

            if node['name'] in names:
                raise ValueError(f'two nodes are named {node["name"]}')

            names.add(node['name'])

            if not isinstance(node.get('configuration'), dict):
                raise ValueError(
                    f'node {node["name"]} needs a "configuration" object'
                )

            if node.get('warped') and not isinstance(
                node.get('warp_configuration'), dict
            ):
                raise ValueError(
                    f'node {node["name"]} is warped: it needs a '
                    '"warp_configuration" object'
                )

        # the same check warmup() runs
        check_links(pipeline['name'], pipeline['nodes'], pipeline['links'])

        if not isinstance(pipeline.get('log_extra') or dict(), dict):
            raise ValueError('pipeline "log_extra" must be an object')

        get_transport(pipeline.get('transport'))

        if pipeline.get('telemetry') is not None:
            check_pipeline_telemetry(pipeline)

        return pipeline
