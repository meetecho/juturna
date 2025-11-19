import typing
import time
import json


class Message[T_Input]:
    """
    A message is a container object that all nodes produce and read to and from
    buffers, plus offering few extra utilities.
    """

    __slots__ = [
        '_creator',
        '_version',
        '_payload',
        '_current_timer',
        '_start_timer',
        '_stop_timer',
        'created_at',
        'meta',
        'timers',
    ]

    def __init__(
        self,
        creator: str | None = None,
        version: int = -1,
        payload: T_Input = None,
        timers_from: 'Message' = None,
    ):
        """
        Parameters
        ----------
        creator : str, optional
            The creator of the message. This is the name of the node that
            created the message. The default is None.
        version : int, optional
            The version of the message. This is an integer that indicates the
            version of the data contained in the message. The default is -1.
        payload : Any, optional
            The payload of the message. This is the actual data contained in the
            message. The default is None.
        timers_from : Message
            When provided, timers will be copied from it into the new message.

        """
        self.created_at = time.time()
        self.meta = dict()
        self.timers = (
            dict() if timers_from is None else timers_from.timers.copy()
        )

        self._creator = creator
        self._version = version
        self._payload = payload

        self._current_timer = None
        self._start_timer = None
        self._stop_timer = None

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

    def to_dict(self) -> dict:
        """
        Convert the message to a dictionary representation.

        Returns
        -------
        dict
            A dictionary representation of the message.

        """
        return {
            'created_at': self.created_at,
            'creator': self.creator,
            'version': self.version,
            'payload': self.payload,
            'meta': self.meta,
            'timers': self.timers,
        }

    def to_json(
        self, encoder: typing.Callable | None = None, indent: int | None = None
    ) -> str:
        """
        Convert the message to a JSON string. A custom encoder can be provided
        to serialise non-serialisable content, otherwise the default serialize
        method defined on the payload will be used.

        Parameters
        ----------
        encoder : callable, optional
            A custom JSON encoder. The default is None, which uses the default
            JSON encoder.
        indent : int
            Indentation level for the serialisation, Defaulted to None.

        Returns
        -------
        str
            The JSON string representation of the message.

        """
        use_encoder = encoder or (
            self.payload.serialize if self.payload is not None else None
        )

        return json.dumps(
            self.to_dict(),
            default=use_encoder,
            indent=indent,
        )

    @property
    def creator(self) -> str | None:
        """Returns the creator of the message."""
        return self._creator

    @creator.setter
    def creator(self, creator: str | None):
        self._creator = creator

    @property
    def version(self) -> int:
        """Returns the version of the message."""
        return self._version

    @version.setter
    def version(self, data_version: int):
        self._version = data_version

    @property
    def payload(self) -> T_Input:
        """Returns the payload of the message."""
        return self._payload

    @payload.setter
    def payload(self, payload: typing.Any):
        self._payload = payload

    def timer(self, timer_name: str, timer_value: float | None = None):
        """
        Records a timer with the given name and value.
        If no value is provided, the current time is used.

        Parameters
        ----------
        timer_name : str
            The name of the timer.
        timer_value : float, optional
            The value of the timer. If None, the current time is used.

        """
        timer_value = timer_value or time.time()

        self.timers[timer_name] = timer_value

    def timeit(self, timer_name: str) -> typing.Self:
        """
        Start a timer with the given name.
        This method is a context manager that will automatically stop the timer
        when the context is exited.

        Parameters
        ----------
        timer_name : str
            The name of the timer.

        Returns
        -------
        typing.Self
            The current instance of the Message class.

        """
        self._current_timer = timer_name

        return self
