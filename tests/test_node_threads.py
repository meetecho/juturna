import time
import threading
from juturna.components import Message, Node, State
from juturna.payloads import BytesPayload

class SlowNode(Node):
    def update(self, message: Message, **kwargs):
        time.sleep(0.01)

def test_worker_queue_saturation_no_deadlock(wait_for_condition):

    node = SlowNode(node_name="stress_node", pipe_name="test_pipe")
    node.start()

    num_messages = 2000
    real_data = b"data" * 256
    payload = BytesPayload(cnt=real_data)

    try:
        for i in range(num_messages):
            msg = Message(payload=payload, creator="test_source", version=i)
            node.put(msg)

        success = wait_for_condition(
            lambda: node._last_data_source_evt_id == num_messages - 1,
            timeout=25 # 25 seconds should be enough for processing given the sleep in update and queue timeouts
        )

        assert success, f"Deadlock detected: threads did not process all messages in time, last processed ID: {node._last_data_source_evt_id}"

    finally:
        node.stop()

def test_stop_draining_no_deadlock_with_real_work(wait_for_condition):
    node = SlowNode(node_name="draining_node", pipe_name="test_pipe")
    node.start()

    payload = BytesPayload(cnt=b"important_data")

    for i in range(30):
        msg = Message(payload=payload, creator="test_source", version=i)
        node.put(msg)

    def stop_node():
        node.stop()

    stop_thread = threading.Thread(target=stop_node)
    stop_thread.start()

    stop_thread.join(timeout=5) # Wait up to 5 seconds for the thread to finish

    assert not stop_thread.is_alive(), "Deadlock detected in node.stop()"
    assert node._last_data_source_evt_id == 29, f"Not all messages were processed during draining, last processed ID: {node._last_data_source_evt_id}"
