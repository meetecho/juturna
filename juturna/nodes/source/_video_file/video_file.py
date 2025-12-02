"""
VideoFile

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Stream a local video file.
"""

import subprocess
import pathlib
import json
import time

import numpy as np

from juturna.components import Node
from juturna.components import Message
from juturna.payloads import BytesPayload, ImagePayload


class VideoFile(Node[BytesPayload, ImagePayload]):
    """Read video file and steam it locally"""

    def __init__(self, video_path: str, width: int, height: int, **kwargs):
        """
        Parameters
        ----------
        video_path : str
            Path of the source video file.
        width : int
            Output width of the produced video frames.
        height : int
            Output height of the produced video frames.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._video_path = video_path
        self._width = width
        self._height = height

        self._video_info = dict()
        self._sent = 0

        self._ffmpeg_launcher_path = None
        self._ffmpeg_proc = None

    def configure(self):
        """Configure the node"""
        cmd = [
            'ffprobe',
            '-v',
            'quiet',
            '-print_format',
            'json',
            '-show_format',
            '-show_streams',
            str(self._video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        video_stream = next(
            s for s in data['streams'] if s['codec_type'] == 'video'
        )

        self._video_info = {
            'duration': float(data['format'].get('duration', -1)),
            'fps': eval(video_stream.get('r_frame_rate', -1)),
            'width': video_stream['width'],
            'height': video_stream['height'],
            'total_frames': int(video_stream.get('nb_frames', 0)),
        }

        self.logger.info('video info acquired')
        self.logger.info(self._video_info)

    def warmup(self):
        """Warmup the node"""
        self._ffmpeg_launcher_path = self.ffmpeg_launcher

    def start(self):
        """Start the node"""
        self.logger.info('starting file source proc...')

        self._ffmpeg_proc = subprocess.Popen(
            ['sh', self.ffmpeg_launcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=10**8,
        )

        self.set_source(
            lambda: Message[BytesPayload](
                creator=self.name,
                payload=BytesPayload(
                    cnt=self._ffmpeg_proc.stdout.read(
                        self._width * self._height * 3
                    )
                ),
            )
        )

        super().start()

    def stop(self):
        """Stop the node"""
        try:
            self._ffmpeg_proc.stdin.write('q\n')
            self._ffmpeg_proc.stdin.flush()
            self._ffmpeg_proc.stdin.close()

            time.sleep(2)

            self._ffmpeg_proc.terminate()
            self._ffmpeg_proc.wait()
            self._ffmpeg_proc = None
        except Exception:
            ...

        super().stop()

    def destroy(self):
        """Destroy the node"""
        self.stop()

    def update(self, message: Message[BytesPayload]):
        """Receive a message, transmit a message"""
        try:
            full_frame = np.frombuffer(message.payload.cnt, np.uint8).reshape(
                (self._height, self._width, 3)
            )
            to_send = Message(
                creator=self.name,
                version=self._sent,
                payload=ImagePayload(
                    image=full_frame,
                    width=self._width,
                    height=self._height,
                    pixel_format='rgb24',
                    timestamp=time.time(),
                ),
            )

            self.transmit(to_send)
            self._sent += 1
        except Exception as _:
            ...

    @property
    def ffmpeg_launcher(self) -> pathlib.Path:
        """Fetch the FFmpeg launcher script"""
        return self._ffmpeg_launcher_path or self.prepare_template(
            'ffmpeg_launcher.sh.template',
            '_ffmpeg_launcher.sh',
            {
                '_video_path': self._video_path,
                '_frame_shape': f'{self._width}x{self._height}',
            },
        )
