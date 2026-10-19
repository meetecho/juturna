from dataclasses import dataclass
from typing import ClassVar, Protocol

from juturna.transport import TransportBackend


# order of the fields of a record: the page reads them by position
TELEMETRY_FIELDS = (
    'ts',
    'evt',
    'node',
    'origin',
    'msg_id',
    'src_id',
    'size',
    'worker',
)


@dataclass(frozen=True)
class TelemetryContext:
    """What a pipeline hands to the telemetry manager it builds"""

    transport: TransportBackend
    worker: str
    pipe_path: str


class TelemetryManager(Protocol):
    """Collects the telemetry records of a pipeline"""

    # what the transport must offer (see `TransportBackend.capabilities`)
    requires: ClassVar[frozenset[str]]

    def start(self) -> None:
        """Start whatever the manager needs to collect the records"""
        ...

    def stop(self) -> None:
        """Write what is left and release what ``start`` acquired"""
        ...

    def records(self) -> list[tuple]:
        """The records collected so far, oldest first"""
        ...

    def record_telemetry(self, record_batch: list[tuple]) -> None:
        """
        Take a batch of records. It runs in the thread of a node: it must
        never block, and drops the batch rather than slow the node down.
        """
        ...


def tag_records(record_batch: list[tuple], worker: str) -> list[tuple]:
    """Append the worker to every record: message ids collide across workers"""
    return [(*record, worker) for record in record_batch]
