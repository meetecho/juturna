from juturna.components import Message
from juturna.components._buffer import Buffer


def test_buffer_init():
    buffer = Buffer(name='test_buffer')

    assert buffer.name == 'test_buffer'
    assert buffer._received == 0
    assert buffer._this_message is None
    assert buffer._lock is not None


def test_buffer_update():
    buffer = Buffer(name='test_buffer')
    message = Message(creator='test_creator', version=1, payload='test_payload')

    buffer.update(message)

    assert buffer._received == 1
    assert buffer._lock.locked() is False


def test_buffer_update_none():
    buffer = Buffer(name='test_buffer')
    message = None

    buffer.update(message)

    assert buffer._received == 0


def test_buffer_version():
    buffer = Buffer(name='test_buffer')
    message = Message(creator='test_creator', version=1, payload='test_payload')

    buffer.update(message)
    version = buffer.version()

    assert version == 1


def test_buffer_version_empty():
    buffer = Buffer(name='test_buffer')

    version = buffer.version()

    assert version is None


def test_buffer_name():
    buffer = Buffer(name='test_buffer')

    assert buffer.name == 'test_buffer'

    buffer.name = 'new_test_buffer'

    assert buffer.name == 'new_test_buffer'


def test_buffer_update_lock():
    buffer = Buffer(name='test_buffer')
    message = Message(creator='test_creator', version=1, payload='test_payload')

    buffer.update(message)

    assert buffer._lock.locked() is False


def test_buffer_update_lock_with_none():
    buffer = Buffer(name='test_buffer')
    message = None

    buffer.update(message)

    assert buffer._lock.locked() is False


def test_buffer_update_lock_with_message():
    buffer = Buffer(name='test_buffer')
    message = Message(creator='test_creator', version=1, payload='test_payload')

    buffer.update(message)

    assert buffer._lock.locked() is False