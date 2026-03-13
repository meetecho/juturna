"""
JsonDataLoader

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2026-03-11 16:20:39

Read a csv file, transmit rows in JSON format.
"""

import csv

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import ControlSignal
from juturna.payloads import ControlPayload


class CsvDataLoader(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        source_file: str,
        interval: int,
        header: list,
        has_header: bool,
        **kwargs,
    ):
        """
        Parameters
        ----------
        source_file : str
            Path of the csv source file to read.
        interval : int
            How often data should be transmitted.
        header : list
            Keys of the produced object.
        has_header : bool
            If true, skip the first row in the source file.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._source_file = source_file
        self._interval = interval
        self._header = header
        self._has_header = has_header

        self._file = None
        self._reader = None

        self.set_source(self._generate, by=self._interval, mode='pre')

    def _generate(self):
        try:
            return Message[ObjectPayload](
                creator=self.name,
                payload=ObjectPayload.from_dict(
                    {
                        k: v
                        for k, v in zip(
                            self._header, next(self._reader), strict=True
                        )
                    }
                ),
            )
        except StopIteration:
            return Message(
                creator=self.name,
                payload=ControlPayload(ControlSignal.STOP_PROPAGATE),
            )

    def warmup(self):
        """Warmup the node"""
        self._file = open(self._source_file)  # noqa: SIM115
        self._reader = csv.reader(self._file)

        if self._has_header:
            _file_header = next(self._reader)

        if len(self._header) == 0:
            self._header = _file_header

    def start(self):
        """Start the node"""
        super().start()

    def stop(self):
        """Stop the node"""
        super().stop()

        if self._file and not self._file.closed:
            self._file.close()

    def destroy(self):
        """Destroy the node"""
        ...

    def update(self, message: Message[ObjectPayload]):
        """Receive data from upstream, transmit data downstream"""
        self.logger.info(f'transmitting {message}')
        self.transmit(message)
