import typing
import time
import json

from contextlib import contextmanager
from types import MappingProxyType

from juturna.payloads import Draft


class Message[T_Input]:
    """
    A message is a container object that all nodes produce and read to and from
    buffers, plus offering few extra utilities.
    """

    __slots__ = [
        'created_at',
        'creator',
        'version',
        'meta',
        'timers',
        '_payload',
        '_is_frozen',
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
        self.creator = creator
        self.version = version
        self.meta = dict()
        self.timers = (
            dict() if timers_from is None else timers_from.timers.copy()
        )

        self.payload = payload

        object.__setattr__(self, '_is_frozen', False)

    def __repr__(self):
        return f'<Message from {self.creator}, v. {self.version}>'

    def __setattr__(self, key, value):
        if getattr(self, '_is_frozen', False):
            raise TypeError('frozen messages cannot be modified')

        object.__setattr__(self, key, value)

    def __delattr__(self, key):
        if getattr(self, '_is_frozen', False):
            raise TypeError('frozen messages cannot be modified')

        object.__delattr__(self, key)

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
            'meta': dict(self.meta),
            'timers': dict(self.timers),
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

        def default_serializer(obj):
            if hasattr(obj, 'serialize'):
                return obj.serialize(obj)

            raise TypeError(
                f'type {obj.__class__.__name__} is not JSON serializable'
            )

        use_encoder = encoder or default_serializer

        return json.dumps(
            self.to_dict(),
            default=use_encoder,
            indent=indent,
        )

    def freeze(self):
        """Freeze the message, making it immutable."""
        if self._is_frozen:
            return

        if isinstance(self.payload, Draft):
            self.payload = self.payload.compile()

        self.meta = MappingProxyType(self.meta)
        self.timers = MappingProxyType(self.timers)

        object.__setattr__(self, '_is_frozen', True)

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
        if getattr(self, '_is_frozen', False):
            raise TypeError('frozen messages cannot be modified')

        timer_value = timer_value or time.time()

        self.timers[timer_name] = timer_value

    @contextmanager
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
        start = time.time()

        try:
            yield
        finally:
            elapsed = time.time() - start

            self.timer(timer_name, elapsed)
