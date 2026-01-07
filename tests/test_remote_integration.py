
import unittest
import time
import subprocess
import sys
import os
import shutil
import threading
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "juturna" / "remotizer"))
sys.path.insert(0, str(PROJECT_ROOT / "juturna" / "remotizer" / "generated"))

from juturna.remotizer._warp._warp import Warp
from juturna.components import Message
from juturna.payloads import ObjectPayload

class TestRemoteIntegration(unittest.TestCase):
    def setUp(self):
        self.port = 54321
        self.node_name = "test_remote_node"
        self.pipe_name = "test_remote_pipe"
        self.node_mark = "passthrough_identity"
        self.plugins_dir = "plugins"

        # Prepare environment for the server process
        env = os.environ.copy()
        # Add project root AND juturna/remotizer AND generated to PYTHONPATH so 'generated' and sub-modules are found
        env["PYTHONPATH"] = (
            str(PROJECT_ROOT) + os.pathsep +
            str(PROJECT_ROOT / "juturna" / "remotizer") + os.pathsep +
            str(PROJECT_ROOT / "juturna" / "remotizer" / "generated") + os.pathsep +
            env.get("PYTHONPATH", "")
        )

        # Start the server command
        cmd = [
            sys.executable,
            "juturna/remotizer/_remote_service.py",
            "--node-name", self.node_name,
            "--plugins-dir", self.plugins_dir,
            "--pipe-name", self.pipe_name,
            "--node-mark", self.node_mark,
            "--default-config", '{"default_key": "default_val"}',
            "--port", str(self.port)
        ]

        # Start server process
        self.server_process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"Started server process with PID {self.server_process.pid}")

        # Wait a bit for server to start
        time.sleep(2)

        # Check if server died
        if self.server_process.poll() is not None:
            out, err = self.server_process.communicate()
            print(f"Server failed to start:\nSTDOUT:\n{out}\nSTDERR:\n{err}")
            self.fail("Server process died immediately")

    def tearDown(self):
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

            # Print server output for debugging
            out, err = self.server_process.communicate()
            if out or err:
                print(f"--- Server STDOUT ---\n{out}")
                print(f"--- Server STDERR ---\n{err}")

    def test_end_to_end_echo(self):
        # Instantiate the Client (Warp)
        client = Warp(
            grpc_host="127.0.0.1",
            grpc_port=self.port,
            timeout=5,
            remote_config={"foo": "bar"},
            node_name="client_node",
            pipe_name=self.pipe_name
        )

        client.warmup()

        # Create a test message
        # ObjectPayload is a dict subclass but dataclass might interfere with init kwargs
        payload = ObjectPayload.from_dict({"result": "hello remote"})
        msg = Message(
            creator="tester",
            version=1,
            payload=payload
        )

        # We need to capture the output of client.transmit
        # Since client.transmit puts into _destinations queues, we need to mock a destination

        received_messages = []

        class MockDestination:
            def put(self, message):
                received_messages.append(message)

        client.add_destination("mock_dest", MockDestination())

        # Calls client.update -> calls server -> calls node -> returns -> client.transmit
        try:
            client.update(msg)
        except Exception as e:
            self.fail(f"Client update failed: {e}")

        # Verify
        self.assertEqual(len(received_messages), 1)
        response = received_messages[0]

        self.assertIsInstance(response, Message)
        # PassthroughIdentity echoes the payload
        self.assertEqual(response.payload["result"], "hello remote")

        # Verify correlation_id loopback if possible?
        # The client node (Warp) handles the correlation internally and returns the message.
        # The fact that we got a response implies correlation worked!

        # PassthroughIdentity updates creator to its name
        self.assertEqual(response.creator, "test_remote_node")

if __name__ == "__main__":
    unittest.main()
