import pathlib
import tempfile

from juturna import hub


def test_list_plugins():
    plugins = hub.list_plugins()

    assert isinstance(plugins, dict)
    assert 'nodes' in plugins.keys()
    assert 'pipelines' in plugins.keys()


def test_download_node():
    node_name = 'proc/_passthrough_identity'
    hub.download_node(node_name, destination_folder=tempfile.gettempdir())

    assert pathlib.Path(f'{tempfile.gettempdir()}/nodes/{node_name}').exists()


def test_download_pipeline():
    pipeline_name = 'silence_detection'
    hub.download_pipeline(pipeline_name,
                          destination_folder=tempfile.gettempdir())

    assert pathlib.Path(
        f'{tempfile.gettempdir()}/pipelines/{pipeline_name}').exists()
    
    assert pathlib.Path(
        f'{tempfile.gettempdir()}/nodes/proc/_vad_silero').exists()