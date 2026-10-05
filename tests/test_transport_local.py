import contextlib

from juturna.components import Buffer, Node
from juturna.transport import ThreadingTransport


class RecordingTransport(ThreadingTransport):
    """Remembers how each queue was asked for, and the node scopes."""

    def __init__(self):
        super().__init__()

        self.queues = list()
        self.scopes = list()

    def new_queue(self, maxsize: int = 0, local: bool = False):
        self.queues.append(local)

        return super().new_queue(maxsize, local)

    @contextlib.contextmanager
    def node_scope(self, shared: bool):
        self.scopes.append(shared)

        yield


def test_local_hint_gives_a_working_queue():
    queue = ThreadingTransport().new_queue(maxsize=2, local=True)

    queue.put('a')
    queue.put('b')

    assert queue.full(), 'a queue of 2 with 2 items must be full'
    assert queue.get() == 'a', 'the queue must keep the order'
    assert queue.qsize() == 1, f'Expected 1 item, got {queue.qsize()}'


def test_buffer_asks_for_a_local_queue():
    transport = RecordingTransport()

    Buffer('creator', transport=transport)

    assert transport.queues == [True], (
        f'The out queue must be local, got {transport.queues}'
    )


def test_node_inbound_queue_is_not_declared_local():
    transport = RecordingTransport()

    Node(node_name='n', pipe_name='p', transport=transport)

    # first the inbound queue, then the one of its buffer
    assert transport.queues == [False, True], (
        f'Expected [inbound, buffer] = [False, True], got {transport.queues}'
    )
