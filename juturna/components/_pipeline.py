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
        """
        Parameters
        ----------
        config : dict
            The pipeline configuration. This is a dictionary that contains the
            pipeline configuration, including the pipeline name, ID, folder,
            nodes, and links.
        """
        self._raw_config = copy.deepcopy(config)
        self._name = self._raw_config['pipeline']['name']
        self._pipe_id = self._raw_config['pipeline']['id']
        self._pipe_path = self._raw_config['pipeline']['folder']

        self._pipe = dict()

        self._status = PipelineStatus.NEW
        self.created_at = time.time()

    @staticmethod
    def from_json(json_path: str) -> 'Pipeline':
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
    def pipe_path(self) -> str:
        return self._pipe_path

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> dict:
        return {
            'pipe_id': self.pipe_id,
            'folder': self.pipe_path,
            'self': self._status,
            'nodes': {
                n['node'].name: {
                    'status': n['node'].status,
                    'config': n['node'].configuration
                } for n in self._pipe.values()} if self._pipe else dict()
        }

    def warmup(self):
        """Prepare the pipeline and all its nodes.

        This method creates all the concrete nodes in the pipe, allocating
        their required resources.

        """
        if self._status != PipelineStatus.NEW:
            raise RuntimeError(f'pipeline {self.name} cannot be warmed up')
        
        if self._pipe is None:
            self._pipe = dict()

        pathlib.Path(self.pipe_path).mkdir(parents=True, exist_ok=True)

        with open(pathlib.Path(self.pipe_path, 'config.json'), 'w') as f:
            json.dump(self._raw_config, f, indent=2)

        nodes = self._raw_config['pipeline']['nodes']
        links = self._raw_config['pipeline']['links']

        for node in nodes:
            name = node['name']
            node_folder = pathlib.Path(self.pipe_path, name)
            node_folder.mkdir(exist_ok=True)

            _node, _register = _component_builder.build_component(
                node, plugin_dirs=self._raw_config['plugins'])

            _node.name = name
            logging.info(f'SESS: calling configure for node {name}')

            _node.pipe_id = copy.deepcopy(self._pipe_id)
            _node.pipe_path = node_folder
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

    def update_node(self,
                    node_name: str,
                    property_name: str,
                    property_value: typing.Any):
        assert self._pipe is not None
        assert self._pipe.get(node_name, None) is not None

        self._pipe[node_name]['node'].set_on_config(
            property_name, property_value)

    def start(self):
        """
        Start the pipeline and all its nodes.
        This method starts all the nodes in the pipeline, allowing them to
        process data. The nodes are started in reverse order of their
        configuration, ensuring that the source node is the last one to be
        started. This is important to ensure that the data flow is properly
        established and that all nodes are ready to receive data.
        """
        if self._status != PipelineStatus.READY:
            raise RuntimeError(f'pipeline {self.name} is not ready')
        
        if self._pipe is None:
            raise RuntimeError(f'pipeline {self.name} is not configured')

        for node_name in list(self._pipe.keys())[::-1]:
            self._pipe[node_name]['node'].start()

        self._status = PipelineStatus.RUNNING

    def stop(self):
        """
        Stop the pipeline and all its nodes.
        This method stops all the nodes in the pipeline, preventing them from
        processing any further data. The nodes are stopped in reverse order of
        their configuration, ensuring that the source node is the last one to be
        stopped. This is important to ensure that the data flow is properly
        terminated and that all nodes are safely stopped.
        """
        if self._status != PipelineStatus.RUNNING:
            raise RuntimeError(f'pipeline {self.name} is not running')
        
        if self._pipe is None:
            raise RuntimeError(f'pipeline {self.name} is not configured')

        for node_name in list(self._pipe.keys())[::-1]:
            self._pipe[node_name]['node'].stop()

        self._status = PipelineStatus.READY

    def destroy(self):
        """
        Destroy the pipeline and all its nodes.
        This method cleans up all the resources used by the pipeline and its
        nodes. It clears the source and destination buffers for each node,
        destroys the nodes, and removes them from the pipeline. This is
        important to ensure that all resources are properly released and that
        there are no memory leaks. The pipeline is set to None, and garbage
        collection is triggered to free up any remaining resources.
        """
        if self._status == PipelineStatus.RUNNING:
            self.stop()

        if self._pipe is None:
            return

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
