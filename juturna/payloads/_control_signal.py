"""
Control signals

A control signal is an integer enum that can be used as field within a control
payload. Control signals derive from IntEnum, which allows for easy
straightforward serialisation.

**Note**: any control signal with a value less than zero will be associated
with a stop call.
"""

from enum import IntEnum


class ControlSignal(IntEnum):
    STOP_PROPAGATE: int = -2
    STOP: int = -1
    START: int = 0
    START_PROPAGATE: int = 1
    WARMUP: int = 2
    SUSPEND: int = 3
    RESUME: int = 4
