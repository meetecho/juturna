import pytest

from juturna.components import Message
from juturna.components._buffer import Buffer
from juturna.payloads import AudioPayload, Batch


def _buffer(marks):
    """Buffer that holds every message until ``marks(data)`` says otherwise."""
    return Buffer('test', synchroniser=marks)


def _fill(buffer, creator, count, payload=None):
    sent = list()

    for _ in range(count):
        message = Message(creator=creator, payload=payload)
        sent.append(message)
        buffer.put(message)

    return sent


def _hold_until(size, marks):
    def synchroniser(data):
        if sum(len(v) for v in data.values()) < size:
            return dict()

        return marks(data)

    return synchroniser


def test_batch_keeps_messages_oldest_first():
    buffer = _buffer(_hold_until(3, lambda data: {'a': [2, 1, 0]}))
    sent = _fill(buffer, 'a', 3, payload=AudioPayload())

    batch = buffer.get_nowait()

    assert [m.id for m in batch.payload.messages] == [m.id for m in sent]


def test_unsorted_indexes_select_the_requested_messages():
    buffer = _buffer(_hold_until(4, lambda data: {'a': [2, 0]}))
    sent = _fill(buffer, 'a', 4, payload=AudioPayload())

    batch = buffer.get_nowait()

    assert [m.id for m in batch.payload.messages] == [sent[0].id, sent[2].id]
    assert [m.id for m in buffer._data['a']] == [sent[1].id, sent[3].id]


def test_duplicate_and_negative_indexes_select_each_message_once():
    buffer = _buffer(_hold_until(3, lambda data: {'a': [-1, 0, 2, 0]}))
    sent = _fill(buffer, 'a', 3, payload=AudioPayload())

    batch = buffer.get_nowait()

    assert [m.id for m in batch.payload.messages] == [sent[0].id, sent[2].id]
    assert [m.id for m in buffer._data['a']] == [sent[1].id]


def test_out_of_range_index_leaves_the_buffer_unchanged():
    buffer = _buffer(_hold_until(2, lambda data: {'a': [0, 5]}))
    _fill(buffer, 'a', 1)

    with pytest.raises(IndexError, match='index 5 out of range for a'):
        buffer.put(Message(creator='a'))

    assert len(buffer._data['a']) == 2
    assert buffer._out_queue.empty()


def test_batch_of_messages_without_size_is_delivered():
    buffer = _buffer(_hold_until(2, lambda data: {'a': [0], 'b': [0]}))
    _fill(buffer, 'a', 1)
    _fill(buffer, 'b', 1, payload='text')

    batch = buffer.get_nowait()

    assert isinstance(batch.payload, Batch)
    assert batch.payload.size_bytes == 0
    assert buffer._data == {'a': [], 'b': []}


def test_failed_batch_keeps_the_messages_in_the_buffer(monkeypatch):
    def broken_batch(**kwargs):
        raise RuntimeError('cannot build batch')

    monkeypatch.setattr('juturna.components._buffer.Batch', broken_batch)

    buffer = _buffer(_hold_until(2, lambda data: {'a': [0, 1]}))
    _fill(buffer, 'a', 1)

    with pytest.raises(RuntimeError):
        buffer.put(Message(creator='a'))

    assert len(buffer._data['a']) == 2
    assert buffer._out_queue.empty()
