import base64
import copy
import dataclasses
import functools
import sys

from typing import Self
from typing import Any
from dataclasses import field, dataclass

import numpy as np

import juturna.meta as meta


def _to_json(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, bytes | bytearray):
        return base64.b64encode(value).decode('ascii')

    # before the payload check, as ObjectPayload is both
    if isinstance(value, dict):
        return {k: _to_json(v) for k, v in value.items()}

    if isinstance(value, BasePayload):
        return type(value).serialize(value)

    if isinstance(value, list | tuple):
        return [_to_json(v) for v in value]

    return value


@dataclass(frozen=True, slots=True)
class BasePayload:
    def clone(self) -> Self:
        return copy.deepcopy(self)

    @staticmethod
    def serialize(obj) -> dict:
        """
        Convert a dataclass payload into JSON-compatible values, field by
        field: arrays become lists, bytes become base64 text, and nested
        payloads use their own ``serialize``.

        Raises
        ------
        TypeError
            If the payload class is not itself a dataclass, so it has no
            fields to serialise.

        """
        if '__dataclass_fields__' not in vars(type(obj)):
            raise TypeError(
                f'{type(obj).__name__} is not a dataclass: decorate it with '
                '@dataclass or give it its own serialize()'
            )

        return {
            f.name: _to_json(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
        }


@dataclass(frozen=True)
class AudioPayload(BasePayload):
    audio: np.ndarray = field(default_factory=lambda: np.ndarray(0))
    sampling_rate: int = -1
    audio_format: str = ''
    channels: int = -1
    start: float = -1.0
    end: float = -1.0

    @property
    def size_bytes(self) -> int:
        return self.audio.nbytes

    @staticmethod
    def serialize(obj) -> dict:
        return {
            'audio': obj.audio.tolist(),
            'sampling_rate': obj.sampling_rate,
            'channels': obj.channels,
            'audio_format': obj.audio_format,
            'start': obj.start,
            'end': obj.end,
        }


@dataclass(frozen=True)
class ImagePayload(BasePayload):
    image: np.ndarray = field(default_factory=lambda: np.ndarray([0, 0]))
    width: int = -1
    height: int = -1
    depth: int = -1
    pixel_format: str = ''
    timestamp: float = -1.0

    @property
    def size_bytes(self) -> int:
        return self.image.nbytes

    @staticmethod
    def serialize(obj) -> dict:
        return {
            'image': obj.image.tolist(),
            'width': obj.width,
            'height': obj.height,
            'depth': obj.depth,
            'pixel_format': obj.pixel_format,
            'timestamp': obj.timestamp,
        }


@dataclass(frozen=True)
class VideoPayload(BasePayload):
    video: tuple[ImagePayload, ...] = field(default_factory=tuple)
    frames_per_second: float = -1.0
    codec: str = ''
    start: float = -1.0
    end: float = -1.0

    def __post_init__(self):
        # frames are stored as a tuple, so the frozen payload cannot be
        # changed through the list it was built from
        object.__setattr__(self, 'video', tuple(self.video))

    @property
    def size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.video)

    @staticmethod
    def serialize(obj) -> dict:
        return {
            'video': [ImagePayload.serialize(img) for img in obj.video],
            'frames_per_second': obj.frames_per_second,
            'codec': obj.codec,
            'start': obj.start,
            'end': obj.end,
        }


@dataclass(frozen=True)
class BytesPayload(BasePayload):
    cnt: bytes = field(default_factory=lambda: b'')

    @property
    def size_bytes(self) -> int:
        return len(self.cnt)

    @staticmethod
    def serialize(obj) -> dict:
        return {'cnt': base64.b64encode(obj.cnt).decode('ascii')}


@dataclass(frozen=True)
class Batch(BasePayload):
    messages: tuple = field(default_factory=tuple)

    @property
    def size_bytes(self) -> int:
        # messages without a payload, or with a payload that has no size,
        # count as 0
        return sum(getattr(m.payload, 'size_bytes', 0) for m in self.messages)

    @staticmethod
    def serialize(obj) -> list:
        return [msg.to_dict() for msg in obj.messages]


def _unpickle_object_payload(cls: type, items: dict) -> 'ObjectPayload':
    return cls(**items)


_SEQUENCES = (list, tuple, set, frozenset)


def _deep_size(obj: Any, max_visits: int) -> int:
    """
    Estimate the memory held by an object and the values it contains.

    Arrays count their data buffer, payloads their own ``size_bytes``, and
    any other object its ``sys.getsizeof``. Dict keys are not counted (they
    are mostly short strings shared across dicts), each object is counted
    once, and the walk stops after ``max_visits`` steps, returning the size
    found up to that point.
    """
    size = 0
    seen = set()
    pending = [obj]
    visits = 0

    while pending and visits < max_visits:
        visits += 1
        item = pending.pop()

        if id(item) in seen:
            continue

        seen.add(id(item))
        cls = type(item)

        if cls is np.ndarray:
            size += item.nbytes
        elif isinstance(item, dict):
            size += sys.getsizeof(item, 0)
            pending.extend(item.values())
        elif cls in _SEQUENCES:
            size += sys.getsizeof(item, 0)
            pending.extend(item)
        elif isinstance(item, BasePayload):
            size += getattr(item, 'size_bytes', 0)
        else:
            size += sys.getsizeof(item, 0)

    return size


@dataclass(frozen=True)
class ObjectPayload(dict, BasePayload):
    """
    Immutable dictionary payload, with items also readable as attributes.

    Every dict method that changes the content raises ``TypeError``. Only the
    top level is frozen: mutable values (lists, dicts, arrays) can still be
    changed in place, and should be treated as read-only.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @functools.cached_property
    def size_bytes(self) -> int:
        """
        Approximate memory held by the payload and its values, in bytes.

        The size is computed on first access (only telemetry reads it), then
        cached. The walk takes at most ``JUTURNA_PAYLOAD_SIZE_MAX_VISITS``
        steps, so the value is a lower bound for payloads with many nested
        objects, and in-place changes to nested values after the first access
        are not reflected.
        """
        return _deep_size(self, meta.JUTURNA_PAYLOAD_SIZE_MAX_VISITS)

    def _immutable(self, operation: str):
        raise TypeError(
            f"'{type(self).__name__}' object does not support {operation}"
        )

    def __setitem__(self, key: str, value: Any):
        self._immutable('item assignment')

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'"
            ) from None

    def __delitem__(self, key):
        self._immutable('item deletion')

    def __ior__(self, other):
        self._immutable('in-place update')

    def update(self, *args, **kwargs):
        self._immutable('update()')

    def pop(self, *args):
        self._immutable('pop()')

    def popitem(self):
        self._immutable('popitem()')

    def clear(self):
        self._immutable('clear()')

    def setdefault(self, *args):
        self._immutable('setdefault()')

    def __reduce__(self):
        # dict's default pickling reconstructs the instance by calling
        # __setitem__ for each item, which this class always rejects;
        # route through __init__ instead, like __deepcopy__ already does.
        return (_unpickle_object_payload, (self.__class__, dict(self)))

    def __deepcopy__(self, memo) -> Self:
        cls = self.__class__
        kwargs = {}

        if isinstance(self, dict):
            for k, v in self.items():
                kwargs[k] = copy.deepcopy(v, memo)

        return cls(**kwargs)

    @staticmethod
    def from_dict(origin: dict):
        return ObjectPayload(**origin)
