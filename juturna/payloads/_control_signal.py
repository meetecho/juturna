from enum import IntEnum


class ControlSignal(IntEnum):
    STOP_PROPAGATE: int = -2
    STOP: int = -1
    START: int = 0
    START_PROPAGATE: int = 1
    WARMUP: int = 2
    SUSPEND: int = 3
    RESUME: int = 4
