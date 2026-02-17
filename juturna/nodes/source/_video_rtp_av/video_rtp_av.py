"""
VideoRtpAv

@author: Antonio Bevilacqua
@email: b3by.in.th3.sky@gmail.com

Consume RTP video streams using PyAv.
"""

import time
import pathlib
import threading

import av

from juturna.components import Node
from juturna.components import Message
from juturna.components import _resource_broker as rb
from juturna.payloads import BytesPayload, ImagePayload
from juturna.names import PixelFormat


class VideoRtpAv(Node[BytesPayload, ImagePayload]):
    """Node implementation class"""

    _SDP_TEMPLATE_NAME: str = 'remote_source.sdp.template'
    _OPTIONS: dict = {
        'protocol_whitelist': 'file,udp,rtp',
        'buffer_size': '4096',
        'stimeout': '1000000',
        'probesize': '32',
        'analyzeduration': '0',
        'reorder_queue_size': '0',
        'flags': 'low_delay',
        'fflags': 'nobuffer',
    }

    def __init__(
        self,
        rec_host: str,
        rec_port: int | str,
        payload_type: int,
        codec: str,
        encoding_clock_chan: str,
        **kwargs,
    ):
        """
        Parameters
        ----------
        rec_host : str
            Hostname of the remote RTP stream to receive video from.
        rec_port : int | str
            Port of the RTP stream to receive video from. If set to "auto",
            the port will be assigned automatically by the resource broker.
        payload_type : int
            Payload type for the RTP stream.
        codec : str
            The codec used from the remote video source.
        encoding_clock_chan : str
            encoding name/clock rate[/channels] for the RTP stream as defined
            in RFC 4566 (SDP) and in RFC 3555 (MIME type registration for RTP
            payload formats).
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._rec_host = rec_host
        self._rec_port = rec_port
        self._payload_type = payload_type
        self._codec = codec
        self._encoding_clock_chan = encoding_clock_chan

        self._container = None
        self._sdp_file_path = None
        self._t = None
        self._stop_event = threading.Event()
        self._sent = 0

    def configure(self):
        """Configure the node"""
        if self._rec_port == 'auto':
            self._rec_port = rb.get('port')

    def warmup(self):
        """Warmup the node"""
        self._sdp_file_path = self.sdp_descriptor
        self._t = threading.Thread(
            target=self._generate_chunks, args=(), daemon=True
        )

    def start(self):
        """Start the node"""
        self._t.start()
        super().start()

    def stop(self):
        """Stop the node"""
        self._stop_event.set()
        if self._t:
            self._t.join()
        super().stop()

    def update(self, message: Message[ImagePayload]):
        """Receive data from upstream, transmit data downstream"""
        self.transmit(message)

    def _stream_video_blocks(self):
        self._container = None

        try:
            self._container = av.open(
                str(self.sdp_descriptor), options=self._OPTIONS
            )
            self._stream = self._container.streams.video[0]
            self._stream.thread_type = 'AUTO'

            for packet in self._container.demux(self._stream):
                if self._stop_event.is_set():
                    break

                if packet.dts is None:
                    continue

                try:
                    yield from packet.decode()
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f'stream error: {e}')

            raise
        finally:
            if self._container:
                self._container.close()

    def _generate_chunks(self):
        while not self._stop_event.is_set():
            try:
                for frame in self._stream_video_blocks():
                    if self._stop_event.is_set():
                        break

                    full_frame = frame.to_ndarray(format=PixelFormat.RGB24)

                    to_send = Message[ImagePayload](
                        creator=self.name,
                        version=self._sent,
                        payload=ImagePayload(
                            image=full_frame,
                            width=full_frame.shape[1],
                            height=full_frame.shape[0],
                            pixel_format=PixelFormat.RGB24,
                            timestamp=time.time(),
                        ),
                    )

                    self.put(to_send)
                    self._sent += 1
            except Exception as e:
                if not self._stop_event.is_set():
                    self.logger.info(f'source unavailable ({e}), retrying...')
                    self._stop_event.wait(2.0)

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        """Fetch the SDP descriptor file"""
        return self._sdp_file_path or self.prepare_template(
            self._SDP_TEMPLATE_NAME,
            '_session_in.sdp',
            {
                '_remote_rtp_host': self._rec_host,
                '_remote_rtp_port': self._rec_port,
                '_remote_codec': self._codec,
                '_remote_payload_type': self._payload_type,
                '_encoding_clock_chan': self._encoding_clock_chan,
            },
        )
