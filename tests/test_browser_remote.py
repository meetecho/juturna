from juturna.transport import BrowserTransport


def test_destination_is_shared_by_name():
    transport = BrowserTransport()

    first = transport.remote_destination('sink')

    assert transport.remote_destination('sink') is first, (
        'the same node must have one destination'
    )


def test_connect_again_makes_the_destination_forget_its_queue():
    transport = BrowserTransport()
    destination = transport.remote_destination('sink')
    transport.connect('sink', 'handle-1')
    destination._queue = object()

    transport.connect('sink', 'handle-2')

    assert destination._queue is None, (
        'the destination still holds the queue of the node it replaced'
    )
    assert transport._remote_handles['sink'] == 'handle-2', (
        f'Expected the new handle, got {transport._remote_handles["sink"]}'
    )


def test_connect_before_the_destination_exists():
    transport = BrowserTransport()

    transport.connect('sink', 'handle-1')
    destination = transport.remote_destination('sink')

    assert destination._queue is None, 'nothing is attached before a write'
    assert transport._remote_handles['sink'] == 'handle-1'
