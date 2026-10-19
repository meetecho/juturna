import dataclasses
import typing
import time
import json
import itertools

from collections.abc import Iterator
from contextlib import contextmanager
from types import MappingProxyType

import numpy as np

from juturna.payloads import BasePayload
from juturna.payloads import Draft


class _FrozenDict(dict):
    """A dict that rejects every change, used for nested meta values."""

    def _immutable(self, *args, **kwargs):
        raise TypeError('frozen message meta cannot be modified')

    __setitem__ = __delitem__ = __ior__ = _immutable
    update = pop = popitem = clear = setdefault = _immutable

    def __reduce__(self):
        return (dict, (dict(self),))


_SCALARS = frozenset({str, int, float, bool, bytes, type(None)})
_PAYLOAD_FIELDS: dict[type, tuple[str, ...]] = dict()


def _freeze_meta(value: typing.Any) -> typing.Any:
    """Return a read-only copy of a meta value, converting it in depth."""
    if type(value) in _SCALARS:
        return value

    if isinstance(value, dict):
        return _FrozenDict({k: _freeze_meta(v) for k, v in value.items()})

    if isinstance(value, list | tuple):
        return tuple(_freeze_meta(v) for v in value)

    if isinstance(value, set | frozenset):
        return frozenset(value)

    if isinstance(value, np.ndarray):
        value.setflags(write=False)

    return value


def _payload_fields(payload: BasePayload) -> tuple[str, ...]:
    cls = type(payload)

    if cls not in _PAYLOAD_FIELDS:
        _PAYLOAD_FIELDS[cls] = tuple(
            f.name for f in dataclasses.fields(payload)
        )

    return _PAYLOAD_FIELDS[cls]


def _freeze_arrays(payload: typing.Any):
    """
    Make the arrays a payload holds read-only: arrays in its fields (or, for
    an ObjectPayload, in its values), arrays and payloads in list or tuple
    fields, and nested payloads. Arrays nested in plain lists or dicts are
    not reached, so the cost stays independent of the size of nested data.
    """
    if isinstance(payload, np.ndarray):
        payload.setflags(write=False)

        return

    if isinstance(payload, dict):
        children, walk_sequences = payload.values(), False
    elif isinstance(payload, BasePayload):
        names = _payload_fields(payload)
        children = (getattr(payload, name) for name in names)
        walk_sequences = True
    else:
        return

    for child in children:
        if type(child) in _SCALARS:
            continue

        if isinstance(child, np.ndarray):
            child.setflags(write=False)
        elif isinstance(child, BasePayload):
            _freeze_arrays(child)
        elif walk_sequences and type(child) in (list, tuple):
            for item in child:
                if isinstance(item, np.ndarray | BasePayload):
                    _freeze_arrays(item)


class Message[T_Input]:
    """
    A message is a container object that all nodes produce and read to and from
    buffers, plus offering few extra utilities.
    """

    __slots__ = [
        'id',
        'created_at',
        'creator',
        'version',
        'meta',
        'timers',
        '_payload',
        '_is_frozen',
        '_data_source_id',
    ]

    _id_gen = itertools.count()

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
        self.id = next(self.__class__._id_gen)
        self.created_at = time.time()
        self.creator = creator
        self.version = version
        self.meta = dict()
        self.timers = (
            dict() if timers_from is None else timers_from.timers.copy()
        )

        self.payload = payload
        self._data_source_id: int | None = None

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

    def _freeze(self):
        """
        Freeze the message, making it immutable.

        Meta is copied, with nested dicts, lists and sets turned into
        read-only types (lists become tuples). Arrays in the payload and in
        meta become read-only in place, so neither the sender nor any of the
        receivers can change data the others are reading.
        """
        if self._is_frozen:
            return

        if isinstance(self.payload, Draft):
            self.payload = self.payload.compile()

        _freeze_arrays(self.payload)

        self.meta = MappingProxyType(
            {k: _freeze_meta(v) for k, v in self.meta.items()}
        )
        self.timers = MappingProxyType(dict(self.timers))

        object.__setattr__(self, '_is_frozen', True)

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
            'id': self.id,
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

        if timer_value is None:
            timer_value = time.time()

        self.timers[timer_name] = timer_value

    @contextmanager
    def timeit(self, timer_name: str) -> Iterator[None]:
        """
        Time the enclosed block, and store its duration in seconds as a timer
        with the given name when the block exits. The duration is measured
        with a monotonic clock.

        Parameters
        ----------
        timer_name : str
            The name of the timer.

        """
        start = time.perf_counter()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start

            self.timer(timer_name, elapsed)
