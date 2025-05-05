import time
import copy
import json
import pathlib
import gc
import typing
import logging

from juturna.components import _component_builder

from juturna.names import ComponentStatus
from juturna.names import PipelineStatus


class Pipeline:
    """Juturna working pipeline

    A pipeline aggregates nodes to create a data workflow from a source node to
    destination nodes.

    """

    def __init__(self, config: dict):
        self._raw_config = config
        self._name = self._raw_config['pipeline']['name']
        self._pipe_id = self._raw_config['pipeline']['id']
        self._pipe_folder = self._raw_config['pipeline']['folder']

        self._pipe = dict()

        self._status = PipelineStatus.NEW
        self.created_at = time.time()

    @staticmethod
    def from_json(json_path: str) -> typing.Self:
        """
        Create a pipeline starting from the path of the configuration file
        rather than from the actual configuration content.

        Parameters
        ----------
        json_path : str
            The path to the pipeline configuration file.

        Returns
        -------
        Pipeline
            The pipeline object.
        """
        with open(json_path, 'r') as f:
            config = json.load(f)

        return Pipeline(config)

    @property
    def pipe_id(self) -> str:
        return self._pipe_id

    @property
    def pipe_folder(self) -> str:
        return self._pipe_folder

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> dict:
        return {
            'pipe_id': self.pipe_id,
            'folder': self.pipe_folder,
            'self': self._status,
            'nodes': {
                n['node'].name: {
                    'status': n['node'].status,
                    'config': n['node'].configuration
                } for n in self._pipe.values()}
        }

    def warmup(self):
        """Prepare the pipeline and all its nodes.

        This method creates all the concrete nodes in the pipe, allocating
        their required resources.

        """
        if self._status != PipelineStatus.NEW:
            raise RuntimeError(f'pipeline {self.name} cannot be warmed up')

        pathlib.Path(self.pipe_folder).mkdir(parents=True, exist_ok=True)

        with open(pathlib.Path(self.pipe_folder, 'config.json'), 'w') as f:
            json.dump(self._raw_config, f, indent=2)

        nodes = self._raw_config['pipeline']['nodes']
        links = self._raw_config['pipeline']['links']

        for node in nodes:
            name = node['name']
            node_folder = pathlib.Path(self.pipe_folder, name)
            node_folder.mkdir(exist_ok=True)

            _node, _register = _component_builder.build_component(
                node, plugin_dirs=self._raw_config['plugins'])

            _node.name = name
            logging.info(f'SESS: calling configure for node {name}')

            _node.pipe_id = copy.deepcopy(self._pipe_id)
            _node.session_path = node_folder
            _node.status = ComponentStatus.NEW

            if _register:
                _node.add_destination(_register)

            self._pipe[name] = {'node': _node, 'register': _register}

        for link in links:
            from_node = link['from']
            to_node = link['to']

            self._pipe[to_node]['node'].set_source(
                self._pipe[from_node]['register'])

        for node_name in self._pipe.keys():
            logging.info(f'SESS: calling warmup for {node_name}')
            self._pipe[node_name]['node'].warmup()
            self._pipe[node_name]['node'].status = ComponentStatus.CONFIGURED

        self._status = PipelineStatus.READY
        logging.info('warmed up!')

        return

    def start(self):
        if self._status != PipelineStatus.READY:
            raise RuntimeError(f'pipeline {self.name} is not ready')

        for node_name in list(self._pipe.keys())[::-1]:
            self._pipe[node_name]['node'].start()

        self._status = PipelineStatus.RUNNING

    def stop(self):
        if self._status != PipelineStatus.RUNNING:
            raise RuntimeError(f'pipeline {self.name} is not running')

        for node_name in list(self._pipe.keys())[::-1]:
            self._pipe[node_name]['node'].stop()

        self._status = PipelineStatus.READY

    def destroy(self):
        if self._status == PipelineStatus.RUNNING:
            self.stop()

        for node_name in list(self._pipe.keys())[::-1]:
            logging.info('clearing source...')
            self._pipe[node_name]['node'].clear_source()

            logging.info('clearing destinations...')
            self._pipe[node_name]['node'].clear_destinations()

            self._pipe[node_name]['node'].destroy()

            self._pipe[node_name]['node'] = None
            self._pipe[node_name]['register'] = None

        self._pipe = None

        gc.collect()
