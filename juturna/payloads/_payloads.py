from typing import List
from dataclasses import dataclass

import numpy as np


@dataclass
class AudioPayload:
    audio: np.ndarray
    sampling_rate: int
    channels: int
    start: float
    end: float


@dataclass
class ImagePayload:
    image: np.ndarray
    width: int
    height: int 
    pixel_format: str
    timestamp: float


@dataclass
class VideoPayload:
    video: List[ImagePayload]
    frames_per_second: float
    start: float
    end: float


@dataclass
class BytesPayload:
    cnt: bytes


@dataclass
class ObjectPayload(dict):
    ...