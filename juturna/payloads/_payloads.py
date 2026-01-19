import copy
import json
import sys

from typing import Self
from typing import Any
from dataclasses import dataclass
from dataclasses import field

import numpy as np

from juturna.payloads._control_signal import ControlSignal


@dataclass(frozen=True, slots=True)
class BasePayload:
    def clone(self) -> Self:
        return copy.deepcopy(self)

    @staticmethod
    def serialize(obj):
        return json.JSONEncoder.default(obj)


@dataclass(frozen=True)
class ControlPayload(BasePayload):
    signal: ControlSignal = ControlSignal.STOP


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
        return {'cnt': obj.cnt.decode('utf-8')}


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


@dataclass(frozen=True)
class ObjectPayload(dict, BasePayload):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'size_bytes', sys.getsizeof(self))

    # def __post_init__(self):
    #     object.__setattr__(self, 'size_bytes', sys.getsizeof(self))

    def __setitem__(self, key: str, value: Any):
        raise TypeError(
            f"'{type(self).__name__}' object does not support item assignment"
        )

    def __getattr__(self, key: str) -> Any:
        return self[key]

    def __delitem__(self, key):
        raise TypeError(
            f"'{type(self).__name__}' object does not support item deletion"
        )

    @staticmethod
    def from_dict(origin: dict):
        return ObjectPayload(**origin)
