import contextlib

from juturna.components import Buffer, Node, Pipeline
from juturna.transport import ThreadingTransport

from tests.test_pipeline_workers import Collector, _config


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

    def remote_destination(self, node_name):
        return Collector()


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


def test_pipeline_tells_which_nodes_are_written_to_from_afar(tmp_path):
    transport = RecordingTransport()
    main = Pipeline(_config(tmp_path))
    main._transport = transport
    main.warmup()

    other_transport = RecordingTransport()
    other = Pipeline(_config(tmp_path), worker='b')
    other._transport = other_transport
    other.warmup()

    assert transport.scopes == [False], (
        f'The source has no upstream in another worker: {transport.scopes}'
    )
    assert other_transport.scopes == [True], (
        f'The sink is written to from another worker: {other_transport.scopes}'
    )


def test_pipeline_of_one_worker_keeps_every_queue_local(tmp_path):
    transport = RecordingTransport()
    pipeline = Pipeline(_config(tmp_path, sink_worker='main'))
    pipeline._transport = transport

    pipeline.warmup()

    assert transport.scopes == [False, False], (
        f'No node is written to from afar: {transport.scopes}'
    )
