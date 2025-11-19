import copy
import math
import json

from typing import Self
from dataclasses import dataclass
from dataclasses import field

import numpy as np

from juturna.components import Message


@dataclass
class BasePayload:
    def clone(self) -> Self:
        return copy.deepcopy(self)

    @staticmethod
    def serialize(obj):
        return json.JSONEncoder.default(obj)


@dataclass
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


@dataclass
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


@dataclass
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


@dataclass
class BytesPayload(BasePayload):
    cnt: bytes = field(default_factory=lambda: b'')

    @staticmethod
    def serialize(obj) -> dict:
        return {'cnt': obj.cnt.decode('utf-8')}


@dataclass
class Batch(BasePayload):
    messages: list[Message] = field(default_factory=lambda: list())

    @staticmethod
    def serialize(obj) -> list:
        return [msg.serialize() for msg in obj.messages]


@dataclass
class ObjectPayload(dict, BasePayload):
    @staticmethod
    def from_dict(origin: dict):
        obj = ObjectPayload()

        for k, v in origin.items():
            obj[k] = v

        return obj
