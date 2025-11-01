import copy

from typing import Self
from dataclasses import dataclass
from dataclasses import field

import numpy as np

from juturna.components import Message


@dataclass
class BasePayload:
    def clone(self) -> Self:
        return copy.deepcopy(self)


@dataclass
class AudioPayload(BasePayload):
    audio: np.ndarray = field(default_factory=lambda: np.ndarray(0))
    sampling_rate: int = -1
    channels: int = -1
    start: float = -1.0
    end: float = -1.0


@dataclass
class ImagePayload(BasePayload):
    image: np.ndarray = field(default_factory=lambda: np.ndarray([0, 0]))
    width: int = -1
    height: int = -1
    depth: int = -1
    pixel_format: str = ''
    timestamp: float = -1.0


@dataclass
class VideoPayload(BasePayload):
    video: list[ImagePayload] = field(default_factory=lambda: list())
    frames_per_second: float = -1.0
    start: float = -1.0
    end: float = -1.0


@dataclass
class BytesPayload(BasePayload):
    cnt: bytes = field(default_factory=lambda: b'')


@dataclass
class Batch(BasePayload):
    messages: list[Message] = field(default_factory=lambda: list())


@dataclass
class ObjectPayload(dict, BasePayload):
    @staticmethod
    def from_dict(origin: dict):
        obj = ObjectPayload()

        for k, v in origin.items():
            obj[k] = v

        return obj
