import pathlib
import subprocess
import threading
import time
import contextlib

import numpy as np

from juturna.components import _resource_broker as rb
from juturna.components import Message
from juturna.components import Node
from juturna.payloads import BytesPayload, AudioPayload
from juturna.names import ComponentStatus


class AudioRTP(Node[BytesPayload, AudioPayload]):
    """Source node for streaming audio"""

    _SDP_TEMPLATE_NAME: str = 'remote_source.sdp.template'
    _FFMPEG_TEMPLATE_NAME: str = 'ffmpeg_launcher.sh.template'

    def __init__(
        self,
        rec_host: str,
        rec_port: int,
        audio_rate: int,
        block_size: int,
        channels: int,
        process_log_level: str,
        payload_type: int,
        encoding_clock_chan: str,
        **kwargs,
    ):
        """
        Parameters
        ----------
        rec_host : str
            Hostname of the remote RTP server to receive audio from.
        rec_port : int
            Port of the RTP server to receive audio from. If set to 0,
            the port will be assigned automatically by the resource broker.
        audio_rate : int
            Internal audio sample rate in Hz (samples per seconds).
        block_size : int
            Size of the audio block to sample, in seconds.
        channels : int
            Number of internal audio channels.
        process_log_level : str
            Log level for the ffmpeg process.
        payload_type : int
            Payload type for the RTP stream.
        encoding_clock_chan : str
            encoding name/clock rate[/channels] for the RTP stream as defined
            in RFC 4566 (SDP) and in RFC 3555 (MIME type registration for RTP payload formats).
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._audio_rate = audio_rate
        self._block_size = block_size
        self._payload_type = payload_type
        self._channels = channels
        self._encoding_clock_chan = encoding_clock_chan
        self._rec_bytes = int(
            np.dtype(np.int16).itemsize
            * self._channels
            * self._block_size
            * self._audio_rate
        )
        self._abs_recv = 0

        # infer incoming channel by encoding_clock_chan
        self._in_channels = AudioRTP._parse_audio_channels(encoding_clock_chan)

        self._rec_host = rec_host
        self._rec_port = rec_port
        self._process_log_level = process_log_level

        self._sdp_file_path = None
        self._ffmpeg_proc = None
        self._ffmpeg_launcher_path = None
        self._monitor_thread = None

        # avoid sleep and race conditions during restart using a flag and a lock
        self._stop_requested = False
        self._subprocess_running = False
        self._restart_lock = threading.Lock()

    def configure(self):
        if self._rec_port == 0:
            self._rec_port = rb.get('port')

    def warmup(self):
        self._sdp_file_path = self.sdp_descriptor
        self._ffmpeg_launcher_path = self.ffmpeg_launcher

    def start(self):
        self.logger.debug('starting ffmpeg process...')
        self._stop_requested = False
        self._start_ffmpeg_process()
        super().start()

    def stop(self):
        self.logger.debug('stopping node...')
        self._stop_requested = True

        # safe stop procedure if no process exists
        if self._ffmpeg_proc is None:
            self.logger.debug('ffmpeg process is already None, nothing to stop')
            super().stop()
            return

        try:
            # process is still running ?
            if self._ffmpeg_proc.poll() is None:
                self.logger.debug(
                    'attempting graceful shutdown of ffmpeg process...'
                )

                # trying to stop ffmpeg process gracefully (send 'q' to stdin)
                try:
                    if (
                        self._ffmpeg_proc.stdin
                        and not self._ffmpeg_proc.stdin.closed
                    ):
                        self._ffmpeg_proc.stdin.write(b'q\n')
                        self._ffmpeg_proc.stdin.flush()
                        self._ffmpeg_proc.stdin.close()
                        self.logger.debug('sent quit command to ffmpeg')
                except (BrokenPipeError, OSError) as termination_error:
                    self.logger.debug(
                        f'could not send quit command: {termination_error}'
                    )

                # wait for graceful shutdown
                try:
                    self._ffmpeg_proc.wait(timeout=3)
                    self.logger.debug('ffmpeg process exited gracefully')
                except subprocess.TimeoutExpired:
                    self.logger.warning(
                        'ffmpeg did not exit gracefully, terminating...'
                    )

                    # Try SIGTERM
                    self._ffmpeg_proc.terminate()
                    try:
                        self._ffmpeg_proc.wait(timeout=5)
                        self.logger.debug('ffmpeg process terminated')
                    except subprocess.TimeoutExpired:
                        # Force kill as last resort
                        self.logger.warning(
                            'ffmpeg did not terminate, forcing kill...'
                        )
                        self._ffmpeg_proc.kill()
                        self._ffmpeg_proc.wait()
                        self.logger.warning('ffmpeg process killed')

            else:
                self.logger.debug(
                    f'ffmpeg process already exited with code {self._ffmpeg_proc.returncode}'
                )

        except Exception as stopping_error:
            self.logger.exception(
                f'error while stopping ffmpeg process: {stopping_error}'
            )
            # try to kill as last resort
            if self._ffmpeg_proc and self._ffmpeg_proc.poll() is None:
                try:
                    self._ffmpeg_proc.kill()
                    self._ffmpeg_proc.wait()
                except Exception as kill_error:
                    self.logger.error(f'failed to kill process: {kill_error}')

        super().stop()

    def destroy(self):
        self.logger.debug('destroying node...')
        self._stop_requested = True
        self.stop()

        # monitor thread is fully stopped?
        if self._monitor_thread:
            if self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            self._monitor_thread = None

    @property
    def configuration(self) -> dict:
        base_config = super().configuration
        base_config['port'] = self._rec_port

        return base_config

    def update(self, message: Message[BytesPayload]):
        if not self._subprocess_running:
            return

        waveform = AudioRTP._get_waveform(
            message.payload.cnt, self._in_channels
        )

        to_send = Message[AudioPayload](
            creator=self.name,
            version=self._abs_recv,
            payload=AudioPayload(
                audio=waveform,
                sampling_rate=self._audio_rate,
                channels=self._channels,
                start=self._block_size * self._abs_recv,
                end=self._block_size * self._abs_recv + self._block_size,
            ),
        )

        to_send.meta['size'] = self._block_size
        to_send.meta['source_recv'] = self._abs_recv

        self.transmit(to_send)
        self.logger.info(f'transmitting message {to_send.version}')

        self._abs_recv += 1

    def clear_source(self):
        self.logger.debug('clearing source...')
        self.clear_buffer()
        self.set_source(
            lambda: Message[BytesPayload](
                creator=self.name,
                payload=BytesPayload(cnt=b''),
            ),
            1,
            'pre',
        )

    @staticmethod
    def _get_waveform(raw_data: bytes, channels: int) -> np.ndarray:
        waveform = (
            np.frombuffer(raw_data, np.int16).flatten().astype(np.float32)
            / 32768.0
        )

        if channels == 2:
            waveform = np.reshape(waveform, (-1, 2)).sum(axis=1) / 2

        return waveform

    @staticmethod
    def _parse_audio_channels(encoding_clock_chan: str) -> int:
        channels = 1
        with contextlib.suppress(IndexError, ValueError):
            channels = max(1, int(encoding_clock_chan.split('/')[2]))
        return channels

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        return self._sdp_file_path or self.prepare_template(
            AudioRTP._SDP_TEMPLATE_NAME,
            '_session_in.sdp',
            {
                '_remote_rtp_host': self._rec_host,
                '_remote_rtp_port': self._rec_port,
                '_remote_payload_type': self._payload_type,
                '_encoding_clock_chan': self._encoding_clock_chan,
            },
        )

    @property
    def ffmpeg_launcher(self) -> pathlib.Path:
        return self._ffmpeg_launcher_path or self.prepare_template(
            AudioRTP._FFMPEG_TEMPLATE_NAME,
            '_ffmpeg_launcher.sh',
            {
                '_sdp_location': self.sdp_descriptor,
                '_process_log_level': self._process_log_level,
                '_audio_rate': self._audio_rate,
                '_channels': self._channels,
            },
        )

    def monitor_process(self, proc: subprocess.Popen):
        proc.wait()

        returncode = proc.returncode
        self.logger.debug(
            f'subprocess terminated with code: {returncode} '
            f'- current node status: {self.status.name}'
        )

        self._subprocess_running = False
        self.clear_source()
        # only attempt restart if:
        # 1. stop was not explicitly requested
        # 2. node is still in RUNNING state
        if not self._stop_requested and self.status == ComponentStatus.RUNNING:
            self.logger.warning(
                f'subprocess crashed unexpectedly with code {returncode} '
                f'attempting restart in 2 seconds...'
            )

            time.sleep(2)

            # use lock to prevent concurrent restart attempts
            with self._restart_lock:
                # double-check status before restarting
                if (
                    self.status == ComponentStatus.RUNNING
                    and not self._stop_requested
                ):
                    try:
                        self.logger.info(f'subprocess is respawning...')
                        # Don't call stop() to avoid deadlock
                        # Just restart the process directly
                        self._start_ffmpeg_process()
                        self.logger.info(f'subprocess respawned successfully.')
                    except Exception as respawn_error:
                        self.logger.exception(
                            f'failed to restart subprocess: {respawn_error}'
                        )
                else:
                    self.logger.debug(
                        'restart cancelled - node is no longer running'
                    )
        else:
            self.logger.debug(
                'process termination was expected, no restart needed'
            )

    def _start_ffmpeg_process(self):
        if self._subprocess_running:
            return  # already running

        self._ffmpeg_proc = subprocess.Popen(
            ['sh', self.ffmpeg_launcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=64536,
        )

        self._subprocess_running = True
        self.logger.debug('ffmpeg process started, launching monitor thread...')

        # terminate monitor thread if already running
        # if self._monitor_thread and self._monitor_thread.is_alive():
        #     self.logger.debug('previous monitor thread still alive, waiting for it to finish...')
        #     self._monitor_thread.join(timeout=5)
        #     self._monitor_thread = None

        self._monitor_thread = threading.Thread(
            target=self.monitor_process,
            args=(self._ffmpeg_proc,),
            daemon=True,  # ensure thread exits when main program exits
        )
        self._monitor_thread.start()

        self.logger.debug(
            f'setting source with process {self._ffmpeg_proc.pid}'
        )
        self.set_source(
            lambda: Message[BytesPayload](
                creator=self.name,
                payload=BytesPayload(
                    cnt=self._ffmpeg_proc.stdout.read(self._rec_bytes)
                ),
            )
        )
