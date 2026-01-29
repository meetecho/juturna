"""
Data Streamer Node

@author: Paolo Saviano
@email: psaviano@meetecho.com
@created_at: 2026-01-29 14:54:10

Test node. Streaming bytes sequences of configurable length at a configurable
rate.
"""
import numpy as np

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BytesPayload


class DataStreamer(Node[None, BytesPayload]):
    def __init__(
        self,
        bytes_per_message: int,
        rate: float,
        rate_variance: float,
        **kwargs
    ):
        super().__init__(**kwargs)

        self._bytes_per_message = bytes_per_message
        self._rate_variance = rate_variance
        self._rate = rate

        self._transmitted = 0
        self._transmitting = True

        self.set_source(self._generate, by=1/self._rate, mode='pre')

    def _generate(self):

        if self._rate_variance > 0:
            min_bytes = int(self._bytes_per_message * (1 - self._rate_variance))
            max_bytes = int(self._bytes_per_message * (1 + self._rate_variance))
            num_bytes = np.random.randint(min_bytes, max_bytes + 1)
        else:
            num_bytes = self._bytes_per_message

        return Message[BytesPayload](
            creator=self.name,
            version=self._transmitted,
            payload=BytesPayload(
                cnt=DataStreamer.generate_stream(num_bytes)
            )
        )

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    def update(self, message: Message[BytesPayload]):
        self.transmit(message)
        self.dump_json(message, f'message_{self._transmitted}.json')

        self._transmitted += 1

    @staticmethod
    def generate_stream(sample_length_sec: int, sample_rate: int) -> bytes:
        """
        Generate a stream of bytes.

        Args:
            sample_length_sec: Length of the data sample in seconds
            sample_rate: Sampling rate (bytes per second)

        Returns:
            bytes string containing the generated data stream
        """
    def generate_stream(num_bytes: int) -> bytes:
        """
        Generate a stream of bytes.

        Args:
            num_bytes: Number of bytes to generate

        Returns:
            bytes string containing the generated data stream
        """
        # Generate random bytes
        data_stream = np.random.randint(0, 256, size=num_bytes, dtype=np.uint8)

        return data_stream.tobytes()
