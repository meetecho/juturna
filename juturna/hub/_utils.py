import warnings
import pathlib
import urllib
import json

import juturna as jt

from juturna.hub import _gh_utils


def list_plugins(
    repository_url: str = None, authenticate: bool = False
) -> dict:
    """
    Get a list of remote plugins available for download. This method will look
    into the ``JUTURNA_HUB_URL`` repository, and return a dictionary with both
    nodes and pipelines. Nodes are returned as a collection of objects where
    each key is a type of node, and each value is a node name, whilst pipelines
    are returned as names within a list.

    Parameters
    ----------
    repository_url : str
        The repository url to look into. By default this value is None, so the
        search will be performed on the env variable JUTURNA_HUB_URL.
    authenticate : bool
        When true, the request to download the node will be authenticated using
        the access token defined in JUTURNA_HUB_TOKEN. Defaults to False.

    """
    node_folder_url = urllib.parse.urljoin(
        repository_url or jt.meta.JUTURNA_HUB_URL, 'nodes'
    )
    all_nodes = _gh_utils._gh_node_list(node_folder_url, authenticate)

    pipeline_folder_url = urllib.parse.urljoin(
        repository_url or jt.meta.JUTURNA_HUB_URL, 'pipelines'
    )
    all_pipelines = _gh_utils._gh_node_list(pipeline_folder_url, authenticate)

    plugins = dict()

    if all_nodes:
        plugins['nodes'] = {
            pathlib.Path(n).name: [pathlib.Path(m).name for m in v]
            for n, v in all_nodes.items()
        }

    if all_pipelines:
        plugins['pipelines'] = [pathlib.Path(p).name for p in all_pipelines]

    return plugins


def download_node(
    node_name: str,
    destination_folder: str = None,
    authenticate: bool = False,
    repository_url: str = None,
    force: bool = True,
):
    """
    Given a target node, download it locally.

    Parameters
    ----------
    node_name : str
        The name of the remote node to download (starts with the _ character).
    destination_folder : str
        The folder the node will be downloaded to. Defaults to
        JUTURNA_CACHE_DIR when not provided.
    authenticate : bool
        When true, the request to download the node will be authenticated using
        the access token defined in JUTURNA_HUB_TOKEN. Defaults to False.
    repository_url : str
        The repository from which download a node. By default this is None, so
        the node will be downloaded from JUTURNA_HUB_URL.
    force : bool
        Will not download the node if one with the same name already exists in
        the destination folder. Defaults to True.

    """
    node_url = urllib.parse.urljoin(
        repository_url or jt.meta.JUTURNA_HUB_URL, f'nodes/{node_name}'
    )
    node_content = _gh_utils._gh_node_content_list(node_url, authenticate)

    if node_content is None:
        warnings.warn(
            f'requested node does not exist on hub: {node_name}', stacklevel=1
        )

        return

    target_dir = (
        pathlib.Path(destination_folder)
        if destination_folder
        else pathlib.Path(jt.meta.JUTURNA_CACHE_DIR, 'plugins')
    )

    if pathlib.Path(target_dir, node_name).exists() and not force:
        warnings.warn(
            f'requested node already download: {node_name}', stacklevel=1
        )

        return

    target_dir.mkdir(parents=True, exist_ok=True)

    for _file_path, _file_url in node_content:
        _file_content = _gh_utils._gh_download_file(_file_url, authenticate)

        remote_path = pathlib.Path(_file_path).parts[1:]
        local_path = pathlib.Path(target_dir, *remote_path)

        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(str(local_path), 'w') as f:
            f.write(_file_content)


def download_pipeline(
    pipe_name: str,
    destination_folder: str = None,
    authenticate: bool = False,
    repository_url: str = False,
    force: bool = False,
):
    """
    Download a pipeline from the Juturna hub
    Given a target pipeline, download it locally. This implies downloading all
    the nodes and files that are part of the pipeline.

    Parameters
    ----------
    pipe_name : str
        The name of the remote pipeline to download.
    destination_folder : str
        The folder the pipeline will be downloaded to. Defaults to
        JUTURNA_CACHE_DIR when not provided.
    authenticate : bool
        When true, the request to download the pipeline will be authenticated
        using the access token defined in JUTURNA_HUB_TOKEN. Defaults to False.
    repository_url : str
        The repository from which download a pipeline. By default this is None,
        so the pipeline will be downloaded from JUTURNA_HUB_URL.
    force : bool
        Will not download the pipeline if one with the same name already exists
        in the destination folder. Defaults to True.

    """
    pipe_url = urllib.parse.urljoin(
        repository_url or jt.meta.JUTURNA_HUB_URL, f'pipelines/{pipe_name}'
    )
    pipe_content = _gh_utils._gh_node_content_list(pipe_url, authenticate)

    if pipe_content is None:
        warnings.warn(
            f'requested pipeline does not exist on hub: {pipe_name}',
            stacklevel=1,
        )

        return

    target_dir = (
        pathlib.Path(destination_folder)
        if destination_folder
        else pathlib.Path(jt.meta.JUTURNA_CACHE_DIR, 'plugins')
    )

    pipe_config_url = [
        i for i in pipe_content if pathlib.Path(i[0]).name == 'config.json'
    ]

    if len(pipe_config_url) == 0:
        warnings.warn(
            f'requested pipeline does not have a config file: {pipe_name}',
            stacklevel=1,
        )

        return

    pipe_config = _gh_utils._gh_download_file(
        pipe_config_url[0][1], authenticate
    )
    pipe_config = json.loads(pipe_config)

    target_dir.mkdir(parents=True, exist_ok=True)

    for _file_path, _file_url in pipe_content:
        _file_content = _gh_utils._gh_download_file(_file_url, authenticate)

        remote_path = pathlib.Path(_file_path).parts[1:]
        local_path = pathlib.Path(target_dir, *remote_path)

        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(str(local_path), 'w') as f:
            f.write(_file_content)

    for _node in pipe_config['pipeline']['nodes']:
        node_url = _node.get('repository', None)

        if node_url is None:
            continue

        if node_url == 'hub':
            node_url = jt.meta.JUTURNA_HUB_URL

        dwl_name = f'{_node["type"]}/_{_node["mark"]}'

        download_node(
            dwl_name, destination_folder, authenticate, node_url, force
        )
