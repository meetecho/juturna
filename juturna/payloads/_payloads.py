import base64
import copy
import functools
import json
import sys

from typing import Self
from typing import Any
from dataclasses import field, dataclass

import numpy as np

import juturna.meta as meta


@dataclass(frozen=True, slots=True)
class BasePayload:
    def clone(self) -> Self:
        return copy.deepcopy(self)

    @staticmethod
    def serialize(obj):
        return json.JSONEncoder.default(obj)


@dataclass(frozen=True)
class AudioPayload(BasePayload):
    audio: np.ndarray = field(default_factory=lambda: np.ndarray(0))
    sampling_rate: int = -1
    audio_format: str = ''
    channels: int = -1
    start: float = -1.0
    end: float = -1.0

    def __post_init__(self):
        object.__setattr__(self, 'size_bytes', self.audio.nbytes)

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

    def __post_init__(self):
        object.__setattr__(self, 'size_bytes', self.image.nbytes)

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
    video: list[ImagePayload] = field(default_factory=lambda: list())
    frames_per_second: float = -1.0
    codec: str = ''
    start: float = -1.0
    end: float = -1.0

    def __post_init__(self):
        object.__setattr__(
            self, 'size_bytes', sum([f.nbytes for f in self.video])
        )

    @staticmethod
    def serialize(obj) -> dict:
        return {
            'video': [img.serialize() for img in obj.video],
            'frames_per_second': obj.frames_per_second,
            'codec': obj.codec,
            'start': obj.start,
            'end': obj.end,
        }


@dataclass(frozen=True)
class BytesPayload(BasePayload):
    cnt: bytes = field(default_factory=lambda: b'')

    def __post_init__(self):
        object.__setattr__(self, 'size_bytes', len(self.cnt))

    @staticmethod
    def serialize(obj) -> dict:
        return {'cnt': base64.b64encode(obj.cnt).decode('ascii')}


@dataclass(frozen=True)
class Batch(BasePayload):
    messages: tuple = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(
            self,
            'size_bytes',
            sum([m.payload.size_bytes for m in self.messages]),
        )

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
        return self[key]

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
