import pathlib
import inspect
import string
import logging

from collections.abc import Callable

from typing import Any

from juturna.components._buffer import Buffer
from juturna.components._bridge import Bridge
from juturna.components._poll_bridge import PollBridge
from juturna.components._stream_bridge import StreamBridge

from juturna.components import Message
from juturna.names import ComponentStatus
from juturna.utils.log_utils import jt_logger


class BaseNode[T_Input, T_Output]:
    """
    Use this class to design custom nodes. BaseNode comes with a number of
    utility methods and fields that can be either used as they are or extended
    in the derived classes.
    """

    def __init__(
        self, node_type: str, node_name: str = '', pipe_name: str = ''
    ):
        """
        Parameters
        ----------
        node_type : str
            The type of node to be created. This field can have the values
            ``source``, ``proc`` or ``sink``, depending on the node being
            created.

        node_name : str
            The name to assign to the node.

        pipe_name : str
            The name of the pipe this node belongs to.

        """
        self._name = node_name
        self._pipe_name = pipe_name

        self._status = None
        self._session_id = None
        self._pipe_path = None

        logger_name = f'{self.pipe_name}.{self._name}'
        bridge_name = f'{logger_name}.bridge'

        self._logger = jt_logger(logger_name)
        self._logger.propagate = True

        self._bridge = (
            StreamBridge(bridge_name)
            if node_type == 'source'
            else PollBridge(bridge_name)
        )

        self._bridge.on_update_received(self.update)

    def __del__(self):
        if self._bridge:
            self.stop()
            self.clear_destinations()
            self.clear_source()

    @property
    def name(self) -> str | None:
        """
        The node symbolic name. This name will also be assigned to the node
        bridge component.

        """
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self._bridge.bridge_id = name

    @property
    def bridge(self) -> Bridge:
        """The node bridge component."""
        return self._bridge

    @bridge.setter
    def bridge(self, bridge: Bridge):
        self._bridge = bridge

    @property
    def status(self) -> ComponentStatus | None:
        return self._status

    @property
    def configuration(self) -> dict:
        return {'name': self.name, 'session_id': self.pipe_id}

    @status.setter
    def status(self, new_status: ComponentStatus):
        self._status = ComponentStatus(new_status)

    @property
    def pipe_name(self) -> str | None:
        """
        Id of the pipe the node belongs to. This will automatically be
        assigned to the node when it is intantiated within a pipeline, but can
        also be set manually. An isolated node not included within a pipeline
        will have a ``None`` value for this field.
        """
        return self._pipe_name

    @pipe_name.setter
    def pipe_name(self, pipe_name: str):
        self._pipe_name = pipe_name

    @property
    def pipe_path(self) -> str | None:
        """
        Path to the pipeline session directory. The node has a dedicated folder
        within the pipeline session directory where it stores its data. This
        will automatically be assigned to the node when it is intantiated within
        a pipeline, but can also be set manually. An isolated node not included
        within a pipeline will have a ``None`` value for this field.
        """
        return self._pipe_path

    @pipe_path.setter
    def pipe_path(self, session_path: str):
        self._pipe_path = session_path

    @property
    def static_path(self) -> pathlib.Path:
        """
        Path to the directory where the node is defined. This is useful for
        storing static files (e.g. configuration files) that are needed by the
        node.
        """
        return pathlib.Path(inspect.getfile(self.__class__)).parent

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def compile_template(self, template_name: str, arguments: dict) -> str:
        """
        Compile a template string

        Parameters
        ----------
        template_name : str
            Path of the template.
        arguments : dict
            Dictionary of template anrguments and their values.

        Returns
        -------
        str
            Compiled template string.

        """
        _template_path = pathlib.Path(self.static_path, template_name)

        with open(_template_path) as f:
            _template_string = f.read()

        _content = string.Template(_template_string).substitute(arguments)

        return _content

    def prepare_template(
        self, template_name: str, file_destination_name: str, arguments: dict
    ) -> pathlib.Path:
        """
        Fetch a template file from the node folder, compile it, and save the
        produced file to the node pipeline folder. The template will be compiled
        with basic substitution of the passed arguments.

        Parameters
        ----------
        template_name : str
            The name of the template file to retrieve in the node folder.
        file_destination_name : str
            The name of the destination file in the node pipeline folder.
        arguments : dict
            The argument values to substitute in the template file.

        Returns
        -------
        pathlib.Path
            The path of the filed compiled and saved from the template.

        Raises
        ------
        ValueError
            If the node is not part of a pipeline, and pipe_path is not set.

        """
        if self.pipe_path is None:
            raise ValueError(
                'pipe_path is not set. '
                'Make sure the node is part of a pipeline.'
            )

        _destination_path = pathlib.Path(self.pipe_path, file_destination_name)
        _content = self.compile_template(template_name, arguments)

        with open(_destination_path, 'w') as f:
            f.write(_content)

        return _destination_path.resolve()

    def dump_json(self, message: Message, file_name: str) -> str | None:
        if self.pipe_path is None:
            return None

        dump_path = pathlib.Path(self.pipe_path, file_name)

        with open(dump_path, 'w') as f:
            f.write(message.to_json(encoder=lambda x: x.tolist()))

        return str(dump_path)

    def set_source(
        self, source: Buffer | Callable, by: int = 0, mode: str = 'post'
    ):
        """
        Set the node source (to be used for ``source`` nodes). The source can be
        either a callable or a buffer. However, source nodes are expected to be
        provided with a callable that will be used to generate the data to be
        transmitted.

        Parameters
        ----------
        source : Union[Buffer, callable]
            The source to be set. This can be either a buffer or a callable.
        by : int, optional
            The time interval (in seconds) between two consecutive calls to the
            source. This parameter is only used if the source is a callable.
            The default is 0.
        mode : str, optional
            Whether to apply the ``by`` timer before or after the source call.
            The default is ``post``, indicating the source function will wait
            for ``by`` seconds before being called. If set to ``pre``, the
            source function will be called and then wait for ``by`` seconds
            before being called again.

        """
        if self._bridge.source is None:
            self._bridge.set_source(source, by, mode)

    def add_destination(self, destination: Buffer | Callable):
        self._bridge.add_destination(destination)

    def clear_source(self):
        self._bridge.unset_source()

    def clear_destinations(self):
        self._bridge._destination_containers = list()
        self._bridge._destination_callbacks = list()

    def transmit(self, message: Message[T_Output]):
        """
        Transmit a message through the bridge. This method is used to send data
        from the node to its destinations. When invoking this method, remember
        that only messages with a newer version with respect to the versions
        stored in their destination buffers will trigger an update in the
        receiving nodes.

        Parameters
        ----------
        message : Message
            The message to be transmitted.

        """
        self._bridge.transmit(message)

    def start(self):
        """
        Start the node and begin processing. This method is called automatically
        when the parent pipeline is started. If you override this method in
        your custom node class, make sure to call the parent method to ensure
        the bridge is started correctly.
        """
        self._bridge.start()
        self._status = ComponentStatus.RUNNING

    def stop(self):
        """
        Stop the node and begin processing. This method is called automatically
        when the parent pipeline is stopped. If you override this method in
        your custom node class, make sure to call the parent method to ensure
        the bridge is stopped correctly.
        """
        self._bridge.stop()
        self._status = ComponentStatus.STOPPED

    def configure(self): ...

    def update(self, message: Message[T_Input]): ...

    def set_on_config(self, prop: str, value: Any): ...

    def warmup(self): ...

    def destroy(self): ...
