import copy
import json

from typing import Self
from typing import Any
from dataclasses import dataclass
from dataclasses import field

import numpy as np


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
    channels: int = -1
    start: float = -1.0
    end: float = -1.0

    @staticmethod
    def serialize(obj) -> dict:
        return {
            'audio': obj.audio.tolist(),
            'sampling_rate': obj.sampling_rate,
            'channels': obj.channels,
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

    @staticmethod
    def serialize(obj) -> dict:
        return {'cnt': obj.cnt.decode('utf-8')}


@dataclass(frozen=True)
class Batch(BasePayload):
    messages: tuple = field(default_factory=tuple)

    @staticmethod
    def serialize(obj) -> list:
        return [msg.serialize() for msg in obj.messages]


@dataclass(frozen=True)
class ObjectPayload(dict, BasePayload):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
