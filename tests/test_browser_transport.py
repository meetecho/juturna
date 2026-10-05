import contextlib
import sys
import types

import numpy as np
import pytest

from juturna.components import Message
from juturna.payloads import AudioPayload
from juturna.transport import BrowserTransport
from juturna.transport import Empty
from juturna.transport import Full
from juturna.transport import _browser
from juturna.transport._browser import _serialize_message


def _audio_message(shape):
    return Message(
        creator='src',
        payload=AudioPayload(
            audio=np.zeros(shape, dtype=np.float32),
            sampling_rate=16000,
            channels=1,
            start=0.0,
            end=0.01,
        ),
    )


def test_array_with_too_many_dimensions_is_rejected():
    with pytest.raises(ValueError, match='5 dimensions'):
        _serialize_message(_audio_message((2, 2, 2, 2, 2)))


def test_array_with_the_most_dimensions_is_accepted():
    meta_json, _, ndim, _, _ = _serialize_message(_audio_message((2, 2, 2, 2)))

    assert ndim == 4, f'Expected 4 dimensions, got {ndim}'
    assert meta_json, 'the metadata of the message must not be empty'


def test_node_scope_is_a_context_manager():
    scope = BrowserTransport().node_scope(shared=True)

    assert isinstance(scope, contextlib.AbstractContextManager), (
        f'node_scope must return a context manager, got {type(scope)}'
    )


class _FakeAtomics:
    """Single-threaded `Atomics` over a plain list standing in for the header."""

    @staticmethod
    def load(arr, i):
        return arr[i]

    @staticmethod
    def store(arr, i, v):
        arr[i] = v

    @staticmethod
    def exchange(arr, i, v):
        old, arr[i] = arr[i], v

        return old

    @staticmethod
    def notify(arr, i):
        return 0


@pytest.fixture
def ring(monkeypatch):
    """A `_BrowserQueue` with a fake header, usable outside a browser."""
    monkeypatch.setitem(
        sys.modules, 'js', types.SimpleNamespace(Atomics=_FakeAtomics)
    )

    q = object.__new__(_browser._BrowserQueue)
    q._header = [0] * _browser._HEADER_INT32_LENGTH
    q._capacity = 2
    q._meta_views = [
        [0] * _browser._SLOT_META_INT32_LENGTH for _ in range(q._capacity)
    ]
    for i, view in enumerate(q._meta_views):
        view[_browser._SLOT_SEQ] = i
    q._max_meta_json_bytes = 4096
    q._max_payload_bytes = 4096
    q._wake_item = None

    return q


def test_put_nowait_wakes_the_reader_with_the_token_it_put(ring):
    token = object()

    ring.put_nowait(token)

    assert ring.get(timeout=0) is token, (
        'the reader must get back the wake token that was put'
    )


def test_wake_token_is_delivered_once(ring):
    ring.put_nowait(object())
    ring.get(timeout=0)

    with pytest.raises(Empty):
        ring.get(timeout=0)


def test_wake_from_another_interpreter_reads_as_empty(ring):
    ring._header[_browser._WAKE] = 1

    with pytest.raises(Empty):
        ring.get(timeout=0)

    assert ring._header[_browser._WAKE] == 0, (
        'the wake flag must be consumed even when there is no token to return'
    )


def _fill(ring):
    """Mark every slot as holding a message, as after `capacity` puts."""
    ring._header[_browser._HEAD] = ring._capacity
    for i, view in enumerate(ring._meta_views):
        view[_browser._SLOT_SEQ] = i + 1


def test_put_nowait_on_a_full_ring_raises_the_transport_full(ring):
    _fill(ring)

    with pytest.raises(Full):
        ring.put_nowait(_audio_message((4,)))


def test_wake_token_does_not_need_a_free_slot(ring):
    _fill(ring)

    ring.put_nowait(object())

    assert ring._header[_browser._WAKE] == 1, (
        'a wake token must not fail on a full ring'
    )


def test_put_still_rejects_items_that_are_not_messages(ring):
    with pytest.raises(NotImplementedError, match='put_nowait'):
        ring.put(object())


class _StubLocalQueue:
    """Stands for the local queue, that needs Pyodide to be built."""

    def __init__(self, capacity):
        self.capacity = capacity


@pytest.fixture
def stub_local_queue(monkeypatch):
    monkeypatch.setattr(_browser, '_BrowserLocalQueue', _StubLocalQueue)


def test_queue_of_a_node_nothing_remote_writes_to_is_local(stub_local_queue):
    transport = BrowserTransport(queue_capacity=8)

    with transport.node_scope(shared=False):
        queue = transport.new_queue()

    assert isinstance(queue, _StubLocalQueue), (
        f'Expected a local queue, got {type(queue).__name__}'
    )
    assert queue.capacity == 8, f'Expected capacity 8, got {queue.capacity}'


def test_local_hint_gives_a_local_queue(stub_local_queue):
    queue = BrowserTransport().new_queue(maxsize=3, local=True)

    assert isinstance(queue, _StubLocalQueue), (
        f'Expected a local queue, got {type(queue).__name__}'
    )
    assert queue.capacity == 3, f'Expected capacity 3, got {queue.capacity}'


def test_node_scope_is_restored_after_the_block():
    transport = BrowserTransport()

    with transport.node_scope(shared=False):
        with transport.node_scope(shared=True):
            assert transport._scope_shared is True

        assert transport._scope_shared is False, (
            'the outer scope must come back after the inner one'
        )

    assert transport._scope_shared is None, 'no scope outside the blocks'
