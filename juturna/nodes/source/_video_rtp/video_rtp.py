import os
import time
import string
import pathlib
import logging

import cv2

from juturna.components import Message
from juturna.components import BaseNode

from juturna.components import _resource_broker as rb


class VideoRTP(BaseNode):
    def __init__(self,
                 rec_host: str,
                 payload_type: str,
                 codec: str,
                 fps: int,
                 mode: str,
                 rate: int,
                 video_duration: float):
        super().__init__('source')

        self._rec_host = rec_host
        self._payload = payload_type
        self._codec = codec

        self._mode = mode
        self._fps = fps
        self._rate = 1 / rate
        self._video_duration = video_duration
        self._buffered_frames = list()

        self._sdp_file_path = None
        self._rec_port = None
        self._capture = None
        self._preframe_tm = -1

        self.frame_width = -1
        self.frame_height = -1

        self.set_source(
            self.read_frame if self._mode == 'still' else self.read_video)

    def configure(self):
        self._rec_port = rb.get('port')
        logging.info(
            f'{self.name}: video source ready on port {self._rec_port}')

    def warmup(self):
        os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = \
            'protocol_whitelist;file,rtp,udp'

    def start(self):
        self._capture = cv2.VideoCapture(str(self.sdp_descriptor))
        self.frame_width = int(self._capture.get(3))
        self.frame_height = int(self._capture.get(4))

        self._preframe_tm = time.time()

        super().start()

    def stop(self):
        self._capture.release()

        super().stop()

    def read_frame(self):
        _, frame = self._capture.read()
        elapsed_time = time.time() - self._preframe_tm

        if elapsed_time < self._rate:
            return None

        self._preframe_tm = time.time()

        return frame

    def read_video(self):
        while len(self._buffered_frames) <= self._video_duration * self._fps:
            frame, _ = self._capture.read()
            self._buffered_frames.append(frame)

        frames = self._buffered_frames[:]
        self._buffered_frames = list()

        return frames

    def update(self, new_frame):
        if new_frame is None:
            return

        to_send = Message(creator=self.name)
        to_send.payload = new_frame
        to_send.meta = {
            'mode': self._mode
        }

        self.transmit(to_send)

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        if self._sdp_file_path:
            return self._sdp_file_path

        sdp_file_template = pathlib.Path(
            self.static_path, 'remote_source.sdp.template')

        session_sdp_file = pathlib.Path(
            self.pipe_path, '_session.sdp')

        sdp_content = {
            '_remote_rtp_host': self._rec_host,
            '_remote_rtp_port': self._rec_port,
            '_remote_codec': self._codec,
            '_remote_payload_type': self._payload
        }

        with open(sdp_file_template, 'r') as f:
            _sdp_template = f.read()

        _local_sdp = string.Template(_sdp_template).substitute(sdp_content)

        with open(session_sdp_file, 'w') as f:
            f.write(_local_sdp)

        self._sdp_file_path = session_sdp_file.resolve()

        return self._sdp_file_path
