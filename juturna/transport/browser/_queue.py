import collections
import logging

from typing import Any

from juturna.transport._base import Empty
from juturna.transport._base import Full
from juturna.transport.browser._js import _atomics_wait_async
from juturna.transport.browser._js import _now_ms
from juturna.transport.browser._wire import DEFAULT_QUEUE_CAPACITY
from juturna.transport.browser._wire import DEFAULT_MAX_META_JSON_BYTES
from juturna.transport.browser._wire import DEFAULT_MAX_PAYLOAD_BYTES
from juturna.transport.browser._wire import _serialize_message
from juturna.transport.browser._wire import _deserialize_message

# Slot layout inside the SharedArrayBuffer of a queue:
#
#   queue header, 8 x int32: HEAD, TAIL, COUNT, CLOSED, the geometry
#   (capacity, max_meta_json_bytes, max_payload_bytes), _WAKE
#
#   then `capacity` slots, each of:
#
#   [0..36)                       9 x int32: metaJsonLen, dtypeCode, ndim,
#                                 shape0..shape3, payloadLen, SEQ
#   [36..36+max_meta_json_bytes)  UTF-8 JSON metadata
#   [..end)                       payload bytes (the array reinterpreted
#                                 as uint8, or pickled bytes)
#
# The web api closes and repairs queues from JavaScript (ring.js there): keep
# the two in step. A slot with metaJsonLen 0 holds no message: the page fills
# one in for a producer that died (see `_TOMBSTONE`), and `get()` skips it.
_HEADER_INT32_LENGTH = 8
_HEAD, _TAIL, _COUNT, _CLOSED = 0, 1, 2, 3
# the geometry lets a queue attached from another Worker check that it agrees
# with the creator's: a mismatch would otherwise read mid-slot, silently
_GEOM_CAPACITY, _GEOM_META_BYTES, _GEOM_PAYLOAD_BYTES = 4, 5, 6
# set by `put_nowait()` with a non-message token, to wake the reader
_WAKE = 7
# 8 words describing the message, then the slot's sequence number
_SLOT_META_INT32_LENGTH = 9
_SLOT_SEQ = 8

_WOKEN = -2


def _get_buffer_write_fn():
    """
    Build the JS helper that writes a buffer into a view without copying it
    through `pyodide.ffi`, which measured ~125 ms per frame.
    """
    from js import Function

    return Function.new(
        'destView',
        'srcBufferProtocolObj',
        'const buf = srcBufferProtocolObj.getBuffer("u8"); '
        'try { destView.set(buf.data); } finally { buf.release(); }',
    )


class _BrowserQueue:
    """
    Queue backed by a `SharedArrayBuffer` ring buffer.

    Any number of Workers may write to it (`handle()` gives what to post to
    another one, which attaches by passing the `sab` to a new queue) and
    exactly one reads from it.

    Each slot carries a sequence number. A producer claims ticket `t` with a
    compare-and-swap on the head only if slot `t % capacity` is free for it
    (its sequence is `t`), writes the slot, then publishes it by setting the
    sequence to `t + 1`; the consumer reads the slot once its sequence is
    `t + 1` and frees it for the next lap with `t + capacity`. A producer that
    finds the ring full claims nothing, so a `put()` that times out leaves no
    hole behind.

    A closed queue refuses writes with `QueueClosed` and keeps serving what it
    holds. The page closes the queues of a Worker it lost, and publishes an
    empty slot for a producer that died between claiming and publishing
    (`poisonRing` and `repairRing` in the web api), which `get()` skips.

    Tickets are 32 bits: the ring stays correct past 2**31 messages only if
    `capacity` divides 2**32.
    """

    def __init__(
        self,
        capacity: int = DEFAULT_QUEUE_CAPACITY,
        max_meta_json_bytes: int = DEFAULT_MAX_META_JSON_BYTES,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        sab=None,
    ):
        """
        Create a ring, or attach to the one created elsewhere with the
        `sab` of its handle, whose geometry must then match (`ValueError`).
        """
        from js import Atomics
        from js import Int32Array
        from js import SharedArrayBuffer
        from js import Uint8Array

        self._capacity = capacity
        self._max_meta_json_bytes = max_meta_json_bytes
        self._max_payload_bytes = max_payload_bytes
        self._slot_bytes = (
            _SLOT_META_INT32_LENGTH * 4
            + max_meta_json_bytes
            + max_payload_bytes
        )

        size = _HEADER_INT32_LENGTH * 4 + capacity * self._slot_bytes
        geometry = (capacity, max_meta_json_bytes, max_payload_bytes)

        if sab is None:
            sab = SharedArrayBuffer.new(size)
            header = Int32Array.new(sab, 0, _HEADER_INT32_LENGTH)

            for index, value in zip(
                (_GEOM_CAPACITY, _GEOM_META_BYTES, _GEOM_PAYLOAD_BYTES),
                geometry,
                strict=True,
            ):
                Atomics.store(header, index, value)

            creating = True
        else:
            creating = False
            header = Int32Array.new(sab, 0, _HEADER_INT32_LENGTH)
            found = tuple(
                int(Atomics.load(header, index))
                for index in (
                    _GEOM_CAPACITY,
                    _GEOM_META_BYTES,
                    _GEOM_PAYLOAD_BYTES,
                )
            )

            if sab.byteLength != size or found != geometry:
                raise ValueError(
                    'cannot attach to the queue: it was created with '
                    f'(capacity, max_meta_json_bytes, max_payload_bytes) = '
                    f'{found}, not {geometry}'
                )

        self._sab = sab
        self._header = header

        slots_base = _HEADER_INT32_LENGTH * 4
        self._meta_views = []
        self._meta_json_views = []
        self._payload_views = []

        for i in range(capacity):
            slot_offset = slots_base + i * self._slot_bytes
            meta_json_offset = slot_offset + _SLOT_META_INT32_LENGTH * 4
            payload_offset = meta_json_offset + max_meta_json_bytes

            self._meta_views.append(
                Int32Array.new(sab, slot_offset, _SLOT_META_INT32_LENGTH)
            )
            self._meta_json_views.append(
                Uint8Array.new(sab, meta_json_offset, max_meta_json_bytes)
            )
            self._payload_views.append(
                Uint8Array.new(sab, payload_offset, max_payload_bytes)
            )

            if creating:
                Atomics.store(self._meta_views[i], _SLOT_SEQ, i)

        self._write_bulk = _get_buffer_write_fn()
        self._wake_item = None

    def handle(self):
        """
        What another Worker needs to attach to this queue: a JS object
        ``{sab, capacity, max_meta_json_bytes, max_payload_bytes}``, meant to
        be posted to it (the buffer is shared, not copied).
        """
        from js import Object
        from pyodide.ffi import to_js

        return to_js(
            {
                'sab': self._sab,
                'capacity': self._capacity,
                'max_meta_json_bytes': self._max_meta_json_bytes,
                'max_payload_bytes': self._max_payload_bytes,
            },
            dict_converter=Object.fromEntries,
        )

    def put(self, item: Any, timeout: float | None = None) -> None:
        from juturna.components._message import Message

        if not isinstance(item, Message):
            raise NotImplementedError(
                'BrowserTransport queues only support Message items '
                f'(got {type(item)!r}); only put_nowait() accepts other '
                'items, as wake tokens'
            )

        meta_json_bytes, dtype_code, ndim, shape, payload_buf = (
            _serialize_message(item)
        )

        if len(meta_json_bytes) > self._max_meta_json_bytes:
            raise ValueError(
                f'serialized message metadata ({len(meta_json_bytes)} '
                f"bytes) exceeds this queue's slot capacity "
                f'({self._max_meta_json_bytes} bytes) - increase '
                'max_meta_json_bytes in the transport of the pipeline: '
                '{"name": "browser", "max_meta_json_bytes": ...}'
            )

        payload_len = getattr(payload_buf, 'nbytes', None)
        if payload_len is None:
            payload_len = len(payload_buf)

        if payload_len > self._max_payload_bytes:
            raise ValueError(
                f'serialized message payload ({payload_len} bytes) '
                f"exceeds this queue's slot capacity "
                f'({self._max_payload_bytes} bytes) - increase '
                'max_payload_bytes in the transport of the pipeline: '
                '{"name": "browser", "max_payload_bytes": ...}'
            )

        slot, ticket = self._reserve_write(timeout)
        if slot == -1:
            raise Full

        shape_padded = (list(shape) + [0, 0, 0, 0])[:4]

        meta_view = self._meta_views[slot]

        try:
            meta_view[0] = len(meta_json_bytes)
            meta_view[1] = dtype_code
            meta_view[2] = ndim
            meta_view[3] = shape_padded[0]
            meta_view[4] = shape_padded[1]
            meta_view[5] = shape_padded[2]
            meta_view[6] = shape_padded[3]
            meta_view[7] = payload_len

            self._write_bulk(self._meta_json_views[slot], meta_json_bytes)
            if payload_len > 0:
                self._write_bulk(self._payload_views[slot], payload_buf)
        except BaseException:
            # the slot is claimed: leaving it unpublished would stop the
            # consumer for good, so publish it empty, which `get()` skips
            meta_view[0] = 0
            self._publish_write(slot, ticket)

            raise

        self._publish_write(slot, ticket)

    def put_nowait(self, item: Any) -> None:
        """
        Put a `Message` if a slot is free, or wake the reader otherwise.

        A non-`Message` item is a wake token, which `Node` puts on stop to
        unblock its worker. It takes no slot, so it cannot fail with `Full`,
        and the reader gets it back if it was put from the same interpreter
        (`Empty` otherwise). A reader not yet blocked sees it at its next
        wait, which its timeout bounds.
        """
        from js import Atomics

        from juturna.components._message import Message

        if isinstance(item, Message):
            self.put(item, timeout=0)
            return

        self._wake_item = item
        Atomics.store(self._header, _WAKE, 1)

        # the reader waits on the sequence of the slot it reads next
        tail = int(Atomics.load(self._header, _TAIL))
        Atomics.notify(
            self._meta_views[_slot_of(tail, self._capacity)], _SLOT_SEQ
        )

    def get(self, timeout: float | None = None) -> Any:
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            remaining = (
                None
                if deadline is None
                else max(0.0, deadline - _now_ms()) / 1000
            )
            slot = self._reserve_read(remaining)

            if slot == _WOKEN:
                if self._wake_item is None:
                    raise Empty

                return self._wake_item

            if slot == -1:
                raise Empty

            try:
                msg = self._read_slot(slot)
            except Exception:
                # a message that cannot be rebuilt here (a class this Worker
                # does not have, a malformed slot) must not stall the queue
                # nor make `get()` raise something other than `Empty`
                logging.getLogger('jt.transport').error(
                    'dropping a message that cannot be read from the queue',
                    exc_info=True,
                )
                msg = _TOMBSTONE
            finally:
                self._release_read(slot)

            # a slot the page filled in for a producer that died: nothing there
            if msg is not _TOMBSTONE:
                return msg

    def get_nowait(self) -> Any:
        return self.get(timeout=0)

    def empty(self) -> bool:
        from js import Atomics

        return int(Atomics.load(self._header, _COUNT)) == 0

    def full(self) -> bool:
        from js import Atomics

        return int(Atomics.load(self._header, _COUNT)) >= self._capacity

    def qsize(self) -> int:
        from js import Atomics

        return int(Atomics.load(self._header, _COUNT))

    def close(self) -> None:
        from js import Atomics

        Atomics.store(self._header, _CLOSED, 1)

        # a consumer waits on the sequence of the slot it reads next, a
        # producer on that of the slot it wants to write: wake them all
        for view in self._meta_views:
            Atomics.notify(view, _SLOT_SEQ)

    # -- internals ------------------------------------------------------

    def _read_slot(self, slot: int):
        import numpy as np

        header = np.asarray(self._meta_views[slot].to_py())
        meta_json_len = int(header[0])
        payload_len = int(header[7])

        if meta_json_len == 0:
            return _TOMBSTONE

        # to_py() copies what it is given, so a view over the whole slot area
        # would make every read cost as much as a maximum-size message, however
        # small the message is: cut the view to the bytes in use first
        meta_json_raw = bytes(
            np.asarray(
                self._meta_json_views[slot].subarray(0, meta_json_len).to_py()
            )
        )
        payload_raw = (
            np.asarray(
                self._payload_views[slot].subarray(0, payload_len).to_py()
            )
            if payload_len > 0
            else np.asarray([], dtype='uint8')
        )

        return _deserialize_message(header, meta_json_raw, bytes(payload_raw))

    def _reserve_write(self, timeout: float | None = None) -> tuple[int, int]:
        """
        Claim the next slot: ``(slot, ticket)``, or ``(-1, -1)`` when the ring
        stays full for `timeout` seconds.
        """
        from js import Atomics

        # Blocks indefinitely when timeout is None, matching
        # queue.Queue.put()'s default (block=True, timeout=None) semantics
        # used by ThreadingTransport. put() turns the sentinel into Full.
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            if int(Atomics.load(self._header, _CLOSED)):
                raise QueueClosed('the queue was closed')

            ticket = int(Atomics.load(self._header, _HEAD))
            slot = _slot_of(ticket, self._capacity)
            cell = self._meta_views[slot]
            seq = int(Atomics.load(cell, _SLOT_SEQ))
            behind = _wrap32(seq - ticket)

            if behind == 0:
                claimed = Atomics.compareExchange(
                    self._header, _HEAD, ticket, _wrap32(ticket + 1)
                )

                if int(claimed) == ticket:
                    return slot, ticket

                continue

            if behind > 0:
                # another producer claimed this ticket first
                continue

            # the slot still holds a message of the previous lap: full
            if deadline is None:
                _atomics_wait_async(cell, _SLOT_SEQ, seq)
                continue

            remaining_ms = deadline - _now_ms()
            if remaining_ms <= 0:
                return -1, -1

            _atomics_wait_async(cell, _SLOT_SEQ, seq, remaining_ms)

    def _publish_write(self, slot: int, ticket: int) -> None:
        from js import Atomics

        cell = self._meta_views[slot]

        Atomics.store(cell, _SLOT_SEQ, _wrap32(ticket + 1))
        Atomics.add(self._header, _COUNT, 1)
        Atomics.notify(cell, _SLOT_SEQ)

    def _reserve_read(self, timeout: float | None) -> int:
        from js import Atomics

        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            tail = int(Atomics.load(self._header, _TAIL))
            slot = _slot_of(tail, self._capacity)
            cell = self._meta_views[slot]
            seq = int(Atomics.load(cell, _SLOT_SEQ))

            if seq == _wrap32(tail + 1):
                return slot

            if int(Atomics.exchange(self._header, _WAKE, 0)):
                return _WOKEN

            if int(Atomics.load(self._header, _CLOSED)):
                return -1

            if deadline is None:
                _atomics_wait_async(cell, _SLOT_SEQ, seq)
                continue

            remaining_ms = deadline - _now_ms()
            if remaining_ms <= 0:
                return -1

            _atomics_wait_async(cell, _SLOT_SEQ, seq, remaining_ms)

    def _release_read(self, slot: int) -> None:
        from js import Atomics

        cell = self._meta_views[slot]
        tail = int(Atomics.load(self._header, _TAIL))

        Atomics.store(self._header, _TAIL, _wrap32(tail + 1))
        Atomics.add(self._header, _COUNT, -1)

        # free the slot for the next lap and wake a producer waiting for it
        Atomics.store(cell, _SLOT_SEQ, _wrap32(tail + self._capacity))
        Atomics.notify(cell, _SLOT_SEQ)


def _wrap32(value: int) -> int:
    """Wrap an integer to the signed 32 bits of an `Int32Array` cell."""
    return (value + 2**31) % 2**32 - 2**31


def _slot_of(ticket: int, capacity: int) -> int:
    return (ticket & 0xFFFFFFFF) % capacity


# What the page publishes in a slot claimed by a producer that died (see
# `repairRing` in the web api): a slot with no metadata, which no message has.
_TOMBSTONE = object()


class QueueClosed(RuntimeError):
    """Raised by a `put()` on a queue that was closed."""


class _BrowserLocalQueue:
    """
    Queue for messages that never leave the Worker: they stay Python objects
    in a `deque`, with no serialization and no copy, and the same capacity as
    a ring would have, so a full queue makes `put()` wait just the same.

    Waiting is cooperative: nothing else runs between a check and the wait
    that follows it, so a counter cell that changes with every `put()` and
    `get()` is all it takes to wake a waiter (the mechanism of the ring).
    """

    def __init__(self, capacity: int):
        from js import Int32Array
        from js import SharedArrayBuffer

        self._items = collections.deque()
        self._capacity = capacity
        self._closed = False
        self._cell = Int32Array.new(SharedArrayBuffer.new(4))

    def put(self, item: Any, timeout: float | None = None) -> None:
        if self._closed:
            raise QueueClosed('the queue was closed')

        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while len(self._items) >= self._capacity:
            if not self._wait(deadline):
                raise Full

            if self._closed:
                raise QueueClosed('the queue was closed')

        self._items.append(item)
        self._changed()

    def get(self, timeout: float | None = None) -> Any:
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while not self._items:
            if self._closed or not self._wait(deadline):
                raise Empty

        item = self._items.popleft()
        self._changed()

        return item

    def get_nowait(self) -> Any:
        return self.get(timeout=0)

    def put_nowait(self, item: Any) -> None:
        self.put(item, timeout=0)

    def empty(self) -> bool:
        return not self._items

    def full(self) -> bool:
        return len(self._items) >= self._capacity

    def qsize(self) -> int:
        return len(self._items)

    def close(self) -> None:
        self._closed = True
        self._changed()

    def handle(self):
        raise RuntimeError('a local queue cannot be shared with another Worker')

    def _changed(self) -> None:
        from js import Atomics

        Atomics.add(self._cell, 0, 1)
        Atomics.notify(self._cell, 0)

    def _wait(self, deadline: float | None) -> bool:
        """Wait for a change; False when the deadline has passed."""
        from js import Atomics

        seen = int(Atomics.load(self._cell, 0))

        if deadline is None:
            _atomics_wait_async(self._cell, 0, seen)

            return True

        remaining_ms = deadline - _now_ms()

        if remaining_ms <= 0:
            return False

        _atomics_wait_async(self._cell, 0, seen, remaining_ms)

        return True
