import pytest
import socket
import time
import threading
import struct
import random
import numpy as np
from pathlib import Path

from juturna.nodes.source._audio_rtp_av.audio_rtp_av import AudioRtpAv
from juturna.components import Message
from juturna.payloads import ControlPayload, ControlSignal

class RTPSender:
    def __init__(self, host="127.0.0.1", port=5005, payload_type=10):
        self.address = (host, port)
        self.payload_type = payload_type
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.rate = 8000
        self.packet_duration = 1.0  # 1 second of audio per tick
        self.samples_per_packet = int(self.rate * self.packet_duration)

        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = 12345

        t = np.linspace(0, self.packet_duration, self.samples_per_packet, endpoint=False)
        audio_samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype('>i2')
        self.audio_data = audio_samples.tobytes()

    def send_tick(self, simulate_network_error=False):
        if simulate_network_error:
            self.sock.close()
            raise OSError("Simulated Network Unreachable")

        header = struct.pack(
            '!BBHII',
            0x80,
            self.payload_type,
            self.sequence_number,
            self.timestamp,
            self.ssrc
        )

        self.sock.sendto(header + self.audio_data, self.address)

        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        self.timestamp += self.samples_per_packet

    def close(self):
        try:
            self.sock.close()
        except:
            pass

def generate_stop_message():
    return Message(payload=ControlPayload(ControlSignal.STOP), creator="test_control", version=999)

class TestAudioRtpAvNetworkResilience:

    @pytest.fixture
    def random_port(self):
        """Genera un porto random superiore a 12000."""
        return random.randint(12001, 65535)

    @pytest.fixture
    def node_params(self, random_port):
        return {
            "host": "127.0.0.1",
            "port": random_port,
            "payload_type": 10,
            "encoding_clock_chan": "PCMU/8000",
            "out_rate": 8000,
            "out_channels": 1,
            "resampler_format": "s16",
            "block_size": 1,
            "flush_partial_on_error": True,
            "node_name": "test_node",
            "pipe_name": "test_pipe",
        }
    @pytest.fixture
    def temp_pipeline_path(self, tmp_path):
        d = tmp_path / "pipeline_data"
        d.mkdir()
        return d

    def test_network_error_and_recovery(self, node_params, temp_pipeline_path):
      node = AudioRtpAv(**node_params)
      node._OPTIONS.update({
            'probesize': '32',
            'analyzeduration': '0',
            'fflags': 'nobuffer',
            'flags': 'low_delay'
        })
      node.pipe_path = Path(temp_pipeline_path)
      node.configure()
      node.warmup()
      node.start()
      time.sleep(1.0)
      sender = RTPSender(port=node_params["port"])

      try:

        for _ in range(12): # 12 * 0.2s = 2.4s
          sender.send_tick()
          time.sleep(0.05)

        print(f"received {node._abs_recv} packets on {node_params['port']} before simulating network error")

        start_wait = time.time()
        while node._abs_recv == 0 and (time.time() - start_wait) < 5:
          time.sleep(0.1)

        assert node._abs_recv == 22, f"Node did not receive initial packets as expected, received {node._abs_recv} packets on {node_params['port']}"

        last_recv = node._abs_recv

        with pytest.raises(OSError):
            sender.send_tick(simulate_network_error=True)

        time.sleep(2.0)

        new_sender = RTPSender(port=node_params["port"])
        for _ in range(12):
          new_sender.send_tick()
          time.sleep(0.05)

        assert node._abs_recv == last_recv + 22, f"Node did not recover from network error as expected {node._abs_recv} packets received on {node_params['port']}"
        new_sender.close()

      finally:
        def stop_node():
            node.put(generate_stop_message())
            node.join()

        stop_thread = threading.Thread(target=stop_node)
        stop_thread.start()

        stop_thread.join(timeout=2)
        sender.close()
