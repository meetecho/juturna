import time
import copy
import json
import pathlib
import gc
import typing

from juturna.components import _component_builder
from juturna.components import Node
from juturna.components._dag import DAG
from juturna.utils.log_utils import jt_logger

from juturna.names import ComponentStatus
from juturna.names import PipelineStatus

from juturna.payloads import ControlSignal


class Pipeline:
    """
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

        self._logger = jt_logger(self._name)

        self._nodes: dict[str, Node] = dict()
        self._links: list = list()
        self._dag: DAG = DAG()

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
        with open(json_path) as f:
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
                node_name: {'status': node.status, 'config': node.configuration}
                for node_name, node in self._nodes.items()
            }
            if self._nodes
            else dict(),
        }

    @property
    def DAG(self) -> DAG:
        return self._dag

    def warmup(self):
        """
        Prepare the pipeline and all its nodes.

        This method creates all the concrete nodes in the pipe, allocating
        their required resources.
        """
        if self._status != PipelineStatus.NEW:
            raise RuntimeError(f'pipeline {self.name} cannot be warmed up')

        pathlib.Path(self.pipe_path).mkdir(parents=True, exist_ok=True)

        with open(pathlib.Path(self.pipe_path, 'config.json'), 'w') as f:
            json.dump(self._raw_config, f, indent=2)

        nodes = self._raw_config['pipeline']['nodes']
        links = self._raw_config['pipeline']['links']

        for node in nodes:
            node_name = node['name']
            node_folder = pathlib.Path(self.pipe_path, node_name)
            node_folder.mkdir(exist_ok=True)

            _node: Node = _component_builder.build_component(
                node,
                plugin_dirs=self._raw_config['plugins'],
                pipe_name=self.name,
            )

            _node.pipe_id = copy.deepcopy(self._pipe_id)
            _node.pipe_path = node_folder
            _node.status = ComponentStatus.NEW

            self._nodes[node_name] = _node
            self._dag.add_node(node_name)

        for link in links:
            from_node = link['from']
            to_node = link['to']

            self._nodes[from_node].add_destination(
                to_node, self._nodes[to_node]
            )

            self._nodes[to_node].origins.append(from_node)

            self._links.append(copy.copy(link))
            self._dag.add_edge(from_node, to_node)

        for node_name, node in self._nodes.items():
            node.warmup()
            node.status = ComponentStatus.CONFIGURED

            self._logger.info(f'warmed up node {node_name}')

        self._status = PipelineStatus.READY
        self._logger.info('pipe warmed up!')

        return

    def update_node(
        self, node_name: str, property_name: str, property_value: typing.Any
    ):
        if node := self._nodes.get(node_name):
            node.set_on_config(property_name, property_value)
        else:
            self._logger.warning(f'node {node_name} not in pipeline')

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

        if not self._nodes:
            raise RuntimeError(f'pipeline {self.name} is not configured')

        for layer in self._dag.BFS()[::-1]:
            for node_name in layer:
                self._logger.info(f'starting node {node_name}')

                self._nodes[node_name].start()

        self._status = PipelineStatus.RUNNING

        self._logger.info('pipe started')

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

        if not self._nodes:
            raise RuntimeError(f'pipeline {self.name} is not configured')

        for node_name, node in self._nodes.items():
            self._logger.info(f'stopping node {node_name}')

            node.stop()

        self._status = PipelineStatus.READY

    def suspend_node(self, node_name: str):
        """
        Suspend a node in the pipeline.
        A pipeline node can be suspended, so it won't process any data until it
        is resumed. A suspended node will keep forwarding received messages to
        its destinations.
        """
        if node := self._nodes.get(node_name):
            node.put(ControlSignal.SUSPEND)

    def resume_node(self, node_name: str):
        """
        Resume a node in the pipeline.
        A suspended node can be resumed, so it will start processing data again.
        """
        if node := self._nodes.get(node_name):
            node.put(ControlSignal.RESUME)

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

        if not self._nodes:
            return

        for node_name in list(self._nodes.keys())[::-1]:
            self._nodes[node_name].clear_source()
            self._nodes[node_name].clear_destinations()
            self._nodes[node_name].destroy()

            self._nodes[node_name] = None

        self._nodes = None

        gc.collect()

        self._logger.info('pipe destroyed')
