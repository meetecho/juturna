import typing
import time
import copy
import json


class Message:
    """Container to move data across the pipeline

    A message is an object that all nodes produce and read to and from buffers.
    """
    def __init__(self,
                 creator: str = None,
                 version: int = -1,
                 payload: typing.Any = None):
        self.created_at = time.time()
        self.meta = dict()

        self._creator = creator
        self._version = version
        self._payload = payload
        self._timers = dict()
        self._current_timer = None

    def __repr__(self):
        return f'<Message from {self._creator}, v. {self._version}>'

    def __enter__(self) -> typing.Self:
        self._start_timer = time.time()

        return self

    def __exit__(self, exec_type, exec_val, exec_tb):
        self._stop_timer = time.time()
        elapsed = self._stop_timer - self._start_timer
        self.timer(f'{self._current_timer}', elapsed)

        self._current_timer = None

    @classmethod
    def from_message(cls,
                     message: typing.Self,
                     keep_meta: bool = False) -> typing.Self:
        msg = Message()
        msg._timers = copy.deepcopy(message.timers)

        if keep_meta:
            msg.meta = copy.deepcopy(message.meta)

        return msg

    def to_dict(self):
        return {
            'created_at': self.created_at,
            'creator': self.created_by,
            'version': self.version,
            'payload': self.payload,
            'meta': self.meta,
            'timers': self.timers
        }

    def to_json(self, encoder = None) -> str:
        return json.dumps(self.to_dict(), default=encoder, indent=2)

    @property
    def created_by(self) -> str:
        return self._creator

    @created_by.setter
    def created_by(self, creator: str):
        self._creator = creator

    @property
    def version(self) -> int:
        return self._version

    @version.setter
    def version(self, data_version: int):
        self._version = data_version

    @property
    def payload(self) -> typing.Any:
        return self._payload

    @payload.setter
    def payload(self, payload: typing.Any):
        self._payload = payload

    @property
    def timers(self) -> dict:
        return self._timers

    def timer(self, timer_name: str, timer_value: float = None):
        timer_value = timer_value or time.time()

        self._timers[timer_name] = timer_value

    def timeit(self, timer_name: str) -> typing.Self:
        self._current_timer = timer_name

        return self
