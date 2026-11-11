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
from juturna.payloads._payloads import _to_json


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


def _thaw_meta(value: typing.Any) -> typing.Any:
    """
    Return a copy of a frozen meta value that can be changed again. Tuples
    and frozensets are kept: nothing tells the ones freezing made from the
    ones the sender wrote. Arrays are shared, and stay read-only.
    """
    if isinstance(value, dict | MappingProxyType):
        return {k: _thaw_meta(v) for k, v in value.items()}

    if isinstance(value, tuple):
        return tuple(_thaw_meta(v) for v in value)

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

    The messages a payload carries (in a field, or in a list or tuple field,
    like those of a Batch) are frozen as well.
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
        elif isinstance(child, Message):
            child._freeze()
        elif walk_sequences and type(child) in (list, tuple):
            for item in child:
                if isinstance(item, np.ndarray | BasePayload):
                    _freeze_arrays(item)
                elif isinstance(item, Message):
                    item._freeze()


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

    def __getstate__(self) -> dict:
        # the read-only views freezing puts on meta and timers cannot be
        # pickled, and copy.copy() and copy.deepcopy() go through here too
        return {
            'id': self.id,
            'created_at': self.created_at,
            'creator': self.creator,
            'version': self.version,
            'meta': dict(self.meta),
            'timers': dict(self.timers),
            'payload': self._payload,
            'data_source_id': self._data_source_id,
            'frozen': self._is_frozen,
        }

    def __setstate__(self, state: dict):
        object.__setattr__(self, '_is_frozen', False)

        self.id = state['id']
        self.created_at = state['created_at']
        self.creator = state['creator']
        self.version = state['version']
        self.meta = state['meta']
        self.timers = state['timers']
        self.payload = state['payload']
        self._data_source_id = state['data_source_id']

        # a frozen message stays frozen: its arrays and nested meta come
        # back writable from a pickle, so they are frozen again
        if state['frozen']:
            self._freeze()

    def copy(self, creator: str | None = None) -> 'Message[T_Input]':
        """
        Return a new message with the content of this one, free to be
        changed. This is how a node gets a message it can edit from one it
        received, as received messages are frozen.

        The copy is a message of its own: it has a new ``id`` and creation
        time. Version, meta and timers are copied, and meta can be changed
        again in depth (lists that freezing turned into tuples stay tuples).
        The payload is the same object: payloads cannot be changed, so
        assign a new one, built with ``Draft`` or ``payload.clone()``, to
        send different data.

        ``copy.copy()`` and ``copy.deepcopy()`` work differently: they
        return the same message again, with the same ``id``, and frozen if
        this one is.

        Parameters
        ----------
        creator : str, optional
            The creator of the new message, usually the name of the node
            making the copy. The creator of this message when not given.

        Returns
        -------
        Message
            The new message, not frozen.

        """
        message = Message(
            creator=self.creator if creator is None else creator,
            version=self.version,
            payload=self._payload,
            timers_from=self,
        )
        message.meta = _thaw_meta(self.meta)

        return message

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
        method defined on the payload will be used. With the default encoder,
        arrays become lists, bytes become base64 text and sets become lists,
        wherever they are: in the payload, in an ``ObjectPayload`` or in meta.

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

            # what json cannot write on its own: arrays, bytes, sets
            converted = _to_json(obj)

            if converted is not obj:
                return converted

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
