import pathlib
import inspect

from typing import Union

from juturna.components._buffer import Buffer
from juturna.components._bridge import Bridge
from juturna.components._poll_bridge import PollBridge
from juturna.components._stream_bridge import StreamBridge

from juturna.components import Message
from juturna.names import ComponentStatus


class BaseNode:
    """
    Use this class to design custom nodes. BaseNode comes with a number of
    utility methods and fields that can be either used as they are or extended
    in the derived classes.

    """
    def __init__(self, node_type: str):
        """
        Parameters
        ----------
        node_type : str
            The type of node to be created. This field can have the values
            ``source``, ``proc`` or ``sink``, depending on the node being
            created.
        """
        self._name = None
        self._status = None
        self._session_id = None
        self._session_path = None

        self._bridge = StreamBridge('') \
            if node_type == 'source' else PollBridge('')

        self._bridge.on_update_received(self.update)

    def __del__(self):
        if self._bridge:
            self.stop()
            self.clear_destinations()
            self.clear_source()

    @property
    def name(self) -> str:
        """
        The node symbolic name. This name will also be assigned to the node
        bridge component.
        """
        return self._name

    @name.setter
    def name(self, node_name: str):
        self._name = node_name
        self._bridge.bridge_id = node_name

    @property
    def bridge(self) -> Bridge:
        """
        The node bridge component.
        """
        return self._bridge

    @bridge.setter
    def bridge(self, bridge: Bridge):
        self._bridge = bridge

    @property
    def status(self) -> ComponentStatus:
        return self._status

    @property
    def configuration(self) -> dict:
        return {
            'name': self.name,
            'session_id': self.session_id
        }

    @status.setter
    def status(self, new_status: ComponentStatus):
        self._status = ComponentStatus(new_status)

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, session_id: str):
        self._session_id = session_id

    @property
    def session_path(self) -> str:
        return self._session_path

    @session_path.setter
    def session_path(self, session_path: str):
        self._session_path = session_path

    @property
    def static_path(self) -> pathlib.Path:
        return pathlib.Path(inspect.getfile(self.__class__)).parent

    def dump_json(self, message: Message, file_name: str):
        with open(pathlib.Path(self.session_path, file_name), 'w') as f:
            f.write(message.to_json(encoder=lambda x: x.tolist()))

    def set_source(self, source: Union[Buffer, callable],
                   by: int = 0,
                   mode: str = 'post'):
        if self._bridge.source is None:
            self._bridge.set_source(source, by, mode)

    def add_destination(self, destination: Union[Buffer, callable]):
        self._bridge.add_destination(destination)

    def clear_source(self):
        self._bridge.unset_source()

    def clear_destinations(self):
        self._bridge._destination_containers = list()
        self._bridge._destination_callbacks = list()

    def transmit(self, message: Message):
        self._bridge.transmit(message)

    def start(self):
        self._bridge.start()
        self._status = ComponentStatus.RUNNING

    def stop(self):
        self._bridge.stop()
        self._status = ComponentStatus.STOPPED

    def configure(self):
        ...

    def update(self):
        ...

    def warmup(self):
        ...

    def destroy(self):
        ...
