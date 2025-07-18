import copy

from typing import List
from typing import Self
from dataclasses import dataclass
from dataclasses import field

import numpy as np


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
    video: List[ImagePayload] = field(default_factory=lambda: list())
    frames_per_second: float = -1.0
    start: float = -1.0
    end: float = -1.0


@dataclass
class BytesPayload(BasePayload):
    cnt: bytes = field(default_factory=lambda: bytes())


@dataclass
class ObjectPayload(dict, BasePayload):
    ...