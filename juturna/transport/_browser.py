"""
Browser transport backend (Pyodide), based on `SharedArrayBuffer` and
`Atomics`, made concurrent by JSPI (JavaScript Promise Integration).

Requirements:

- Pyodide >= 314.0.0, loaded in a module-type Worker through a dynamic
  `import()` of `pyodide.mjs`. Older builds crash on nested
  `callPromising()`.
- The entry point that drives a node (`Node.start()` and what it calls) must
  be invoked from JS with `.callPromising()`. The blocking primitives here
  raise a `RuntimeError` when it is not.

Every `js` and `pyodide.ffi` import is deferred into the methods that need
it, so importing this module works on a desktop interpreter too.

Blocking waits use `run_sync(Atomics.waitAsync(...))`, never the synchronous
`Atomics.wait()`: the loops of a node run as cooperative tasks of the same
event loop (Pyodide has no threads), and a synchronous wait would freeze all
of them.

Differences from `ThreadingTransport`:

- a queue slot has a fixed size: `put()` raises `ValueError` for a message
  that does not fit, instead of growing;
- the capacity of a queue is capped by `DEFAULT_QUEUE_CAPACITY`, not by
  `JUTURNA_MAX_QUEUE_SIZE`, which would pre-allocate hundreds of MB at video
  frame sizes;
- `Image`, `Audio` and `Bytes` payloads take a fast binary path, anything
  else is pickled.
"""

import contextlib
import contextvars
import json
import pickle

from collections.abc import Callable
from typing import Any

from juturna.transport._base import Empty
from juturna.transport._base import Full
from juturna.transport._base import WorkerHandle


# there is no thread identity under JSPI: is_current() reads this instead
_current_worker: contextvars.ContextVar = contextvars.ContextVar(
    '_current_worker', default=None
)


def _require_stack_switching(op: str) -> None:
    """Raise a clear error if `op` would block outside `.callPromising()`"""
    from pyodide.ffi import can_run_sync

    if not can_run_sync():
        raise RuntimeError(
            f'{op} would block, but the current call is not running '
            'inside a stack-switching-enabled entry point. Every code '
            'path that can reach a BrowserTransport wait must be invoked '
            'via `<callable>.callPromising()` on Pyodide >= 314.0.0'
        )


def _atomics_wait_async(
    cell, index: int, expected: int, timeout_ms=None
) -> None:
    """Cooperative `Atomics.wait()`: suspend only the current task"""
    from js import Atomics
    from pyodide.ffi import run_sync

    result = (
        Atomics.waitAsync(cell, index, expected)
        if timeout_ms is None
        else Atomics.waitAsync(cell, index, expected, timeout_ms)
    )

    if result.async_:
        _require_stack_switching('a BrowserTransport wait')
        run_sync(result.value)


# --- wire format -----------------------------------------------------------
# Slot layout inside the SharedArrayBuffer of a queue:
#
#   [0..32)                       8x int32: metaJsonLen, dtypeCode, ndim,
#                                 shape0..shape3, payloadLen
#   [32..32+max_meta_json_bytes)  UTF-8 JSON metadata
#   [..end)                       payload bytes (the array reinterpreted
#                                 as uint8, or pickled bytes)
#
# The queue header holds HEAD, TAIL, COUNT, CLOSED and _WAKE.

_HEADER_INT32_LENGTH = 5
_HEAD, _TAIL, _COUNT, _CLOSED, _WAKE = 0, 1, 2, 3, 4
_SLOT_META_INT32_LENGTH = 8
# the shape of an array takes 4 of those words: that is its most dimensions
_MAX_NDIM = 4

_DTYPE_CODES = {
    'uint8': 1,
    'float32': 2,
    'int16': 3,
    'float64': 4,
    'int32': 5,
}
_DTYPE_BY_CODE = {code: name for name, code in _DTYPE_CODES.items()}

_WOKEN = -2

_KIND_IMAGE = 'image'
_KIND_AUDIO = 'audio'
_KIND_BYTES = 'bytes'
_KIND_PICKLE = 'pickle'

DEFAULT_QUEUE_CAPACITY = 8
DEFAULT_MAX_META_JSON_BYTES = 4096
DEFAULT_MAX_PAYLOAD_BYTES = 2_000_000  # above one 1080p uint8 frame


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


class _BrowserEvent:
    """Event primitive backed by a single Int32 cell in a SharedArrayBuffer."""

    _CELL = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._cell = Int32Array.new(sab)

    def set(self) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 1)
        Atomics.notify(self._cell, self._CELL)

    def clear(self) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 0)

    def is_set(self) -> bool:
        from js import Atomics

        return bool(Atomics.load(self._cell, self._CELL))

    def wait(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            if self.is_set():
                return True

            if deadline is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return False
                _atomics_wait_async(self._cell, self._CELL, 0, remaining_ms)
            else:
                _atomics_wait_async(self._cell, self._CELL, 0)


def _serialize_message(msg) -> tuple[bytes, int, int, tuple[int, ...], Any]:
    """
    Return (meta_json_bytes, dtype_code, ndim, shape, payload_buf).

    dtype_code 0 means the payload is not an array: payload_buf is then raw
    bytes (pickled for the fallback path).
    """
    import numpy as np

    from juturna.payloads import AudioPayload
    from juturna.payloads import BytesPayload
    from juturna.payloads import ImagePayload

    payload = msg.payload

    meta = {
        'id': msg.id,
        'created_at': msg.created_at,
        'creator': msg.creator,
        'version': msg.version,
        'meta': dict(msg.meta),
        'timers': dict(msg.timers),
        'data_source_id': msg._data_source_id,
    }

    if isinstance(payload, ImagePayload):
        arr = payload.image
        meta['kind'] = _KIND_IMAGE
        meta['payload_meta'] = {
            'width': payload.width,
            'height': payload.height,
            'depth': payload.depth,
            'pixel_format': payload.pixel_format,
            'timestamp': payload.timestamp,
        }
        dtype_code, ndim, shape, payload_buf = _array_wire(arr, np)

        return (
            json.dumps(meta).encode('utf-8'),
            dtype_code,
            ndim,
            shape,
            payload_buf,
        )

    if isinstance(payload, AudioPayload):
        arr = payload.audio
        meta['kind'] = _KIND_AUDIO
        meta['payload_meta'] = {
            'sampling_rate': payload.sampling_rate,
            'audio_format': payload.audio_format,
            'channels': payload.channels,
            'start': payload.start,
            'end': payload.end,
        }
        dtype_code, ndim, shape, payload_buf = _array_wire(arr, np)

        return (
            json.dumps(meta).encode('utf-8'),
            dtype_code,
            ndim,
            shape,
            payload_buf,
        )

    if isinstance(payload, BytesPayload):
        meta['kind'] = _KIND_BYTES
        meta['payload_meta'] = {}
        payload_buf = payload.cnt

        return (
            json.dumps(meta).encode('utf-8'),
            _DTYPE_CODES['uint8'],
            1,
            (len(payload_buf),),
            payload_buf,
        )

    # VideoPayload, Batch, ObjectPayload, or any custom payload type: no
    # known binary layout, fall back to pickle. Correct,
    # not on the fast path - Buffer._consume() emits Batch for multi-input
    # nodes, so this is a real path, not a hypothetical.
    meta['kind'] = _KIND_PICKLE
    meta['payload_meta'] = {}
    payload_buf = pickle.dumps(payload)

    return json.dumps(meta).encode('utf-8'), 0, 0, (), payload_buf


def _array_wire(arr, np) -> tuple[int, int, tuple[int, ...], Any]:
    dtype_code = _DTYPE_CODES.get(str(arr.dtype))

    if dtype_code is None:
        raise ValueError(
            f'unsupported array dtype for BrowserTransport: {arr.dtype!r} '
            f'(supported: {sorted(_DTYPE_CODES)})'
        )

    if arr.ndim > _MAX_NDIM:
        raise ValueError(
            f'unsupported array for BrowserTransport: {arr.ndim} dimensions, '
            f'at most {_MAX_NDIM} fit in a queue slot'
        )

    # a reinterpretation, not a conversion: a uint8 destination view would
    # otherwise corrupt float32 audio
    flat_bytes = arr.reshape(-1).view(np.uint8)

    return dtype_code, len(arr.shape), tuple(arr.shape), flat_bytes


def _deserialize_message(header, meta_json_bytes: bytes, payload_bytes):
    import numpy as np

    from juturna.components._message import Message
    from juturna.payloads import AudioPayload
    from juturna.payloads import BytesPayload
    from juturna.payloads import ImagePayload

    meta_json_len, dtype_code, ndim, s0, s1, s2, s3, payload_len = (
        int(x) for x in header[:8]
    )
    shape = tuple(int(x) for x in (s0, s1, s2, s3)[:ndim])

    meta = json.loads(meta_json_bytes[:meta_json_len].decode('utf-8'))
    kind = meta['kind']
    pm = meta['payload_meta']
    raw = bytes(payload_bytes[:payload_len])

    if kind in (_KIND_IMAGE, _KIND_AUDIO):
        arr = np.frombuffer(raw, dtype=_DTYPE_BY_CODE[dtype_code]).reshape(
            shape
        )
        payload = (
            ImagePayload(image=arr, **pm)
            if kind == _KIND_IMAGE
            else AudioPayload(audio=arr, **pm)
        )
    elif kind == _KIND_BYTES:
        payload = BytesPayload(cnt=raw)
    elif kind == _KIND_PICKLE:
        payload = pickle.loads(raw)
    else:
        raise ValueError(f'unknown payload kind on wire: {kind!r}')

    msg = Message(
        creator=meta['creator'], version=meta['version'], payload=payload
    )
    msg.id = meta['id']
    msg.created_at = meta['created_at']
    msg.meta = dict(meta['meta'])
    msg.timers = dict(meta['timers'])
    msg._data_source_id = meta['data_source_id']
    msg._freeze()

    return msg


class _BrowserQueue:
    """Queue backed by a `SharedArrayBuffer` ring buffer"""

    def __init__(
        self,
        capacity: int = DEFAULT_QUEUE_CAPACITY,
        max_meta_json_bytes: int = DEFAULT_MAX_META_JSON_BYTES,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    ):
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

        sab = SharedArrayBuffer.new(
            _HEADER_INT32_LENGTH * 4 + capacity * self._slot_bytes
        )
        self._sab = sab
        self._header = Int32Array.new(sab, 0, _HEADER_INT32_LENGTH)

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

        self._write_bulk = _get_buffer_write_fn()
        self._wake_item = None

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

        slot = self._reserve_write(timeout)
        if slot == -1:
            raise Full

        shape_padded = (list(shape) + [0, 0, 0, 0])[:4]

        meta_view = self._meta_views[slot]
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

        self._publish_write(slot)

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
        Atomics.notify(self._header, _COUNT)

    def get(self, timeout: float | None = None) -> Any:
        slot = self._reserve_read(timeout)

        if slot == _WOKEN:
            if self._wake_item is None:
                raise Empty

            return self._wake_item

        if slot == -1:
            raise Empty

        msg = self._read_slot(slot)
        self._release_read()

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
        Atomics.notify(self._header, _COUNT)

    # -- internals ------------------------------------------------------

    def _read_slot(self, slot: int):
        import numpy as np

        header = np.asarray(self._meta_views[slot].to_py())
        meta_json_len = int(header[0])
        payload_len = int(header[7])

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

    def _reserve_write(self, timeout: float | None = None) -> int:
        from js import Atomics

        # Blocks indefinitely when timeout is None, matching
        # queue.Queue.put()'s default (block=True, timeout=None) semantics
        # used by ThreadingTransport. Returns -1 on timeout, mirroring
        # _reserve_read()'s sentinel - put() turns it into Full.
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            count = int(Atomics.load(self._header, _COUNT))

            if count < self._capacity:
                return int(Atomics.load(self._header, _HEAD))

            if timeout is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return -1
                _atomics_wait_async(self._header, _COUNT, count, remaining_ms)
            else:
                _atomics_wait_async(self._header, _COUNT, count)

    def _publish_write(self, slot: int) -> None:
        from js import Atomics

        head = int(Atomics.load(self._header, _HEAD))
        Atomics.store(self._header, _HEAD, (head + 1) % self._capacity)
        Atomics.add(self._header, _COUNT, 1)
        Atomics.notify(self._header, _COUNT)

    def _reserve_read(self, timeout: float | None) -> int:
        from js import Atomics

        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            count = int(Atomics.load(self._header, _COUNT))

            if count > 0:
                return int(Atomics.load(self._header, _TAIL))

            if int(Atomics.exchange(self._header, _WAKE, 0)):
                return _WOKEN

            if int(Atomics.load(self._header, _CLOSED)):
                return -1

            if timeout is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return -1
                _atomics_wait_async(self._header, _COUNT, count, remaining_ms)
            else:
                _atomics_wait_async(self._header, _COUNT, count)

    def _release_read(self) -> None:
        from js import Atomics

        tail = int(Atomics.load(self._header, _TAIL))
        Atomics.store(self._header, _TAIL, (tail + 1) % self._capacity)
        Atomics.add(self._header, _COUNT, -1)
        Atomics.notify(self._header, _COUNT)


def _now_ms() -> float:
    import time

    return time.time() * 1000


class _BrowserLock:
    """
    Mutual exclusion on an Int32 cell. Not reentrant: `Node` and `Buffer`
    never nest acquisitions.
    """

    _CELL = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._cell = Int32Array.new(sab)

    def __enter__(self):
        from js import Atomics

        while True:
            prev = int(Atomics.compareExchange(self._cell, self._CELL, 0, 1))

            if prev == 0:
                return self

            _atomics_wait_async(self._cell, self._CELL, 1)

    def __exit__(self, *exc_info) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 0)
        Atomics.notify(self._cell, self._CELL, 1)


class _BrowserCondition:
    """Condition variable: a generation counter plus a `_BrowserLock`"""

    _GEN = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._gen_cell = Int32Array.new(sab)
        self._lock = _BrowserLock()

    def __enter__(self):
        self._lock.__enter__()
        return self

    def __exit__(self, *exc_info) -> None:
        self._lock.__exit__(*exc_info)

    def wait_for(
        self, predicate: Callable[[], bool], timeout: float | None = None
    ) -> None:
        from js import Atomics

        if predicate():
            return

        # checked before the lock is released: a raise from the wait would
        # leave the lock released, and the enclosing `with` would release it
        # again
        _require_stack_switching('_BrowserCondition.wait_for()')

        # one deadline for the whole call, like threading.Condition
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while not predicate():
            remaining_ms = None
            if deadline is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return

            # read before the lock is released: a notify in between makes
            # the wait return at once instead of being missed
            gen = int(Atomics.load(self._gen_cell, self._GEN))
            self._lock.__exit__(None, None, None)
            _atomics_wait_async(self._gen_cell, self._GEN, gen, remaining_ms)
            self._lock.__enter__()

    def notify_all(self) -> None:
        from js import Atomics

        Atomics.add(self._gen_cell, self._GEN, 1)
        Atomics.notify(self._gen_cell, self._GEN)


def _get_js_spawn_fn():
    """Build the JS helper that starts a task with stack switching"""
    from js import Function

    return Function.new(
        'pyCallableProxy',
        'return pyCallableProxy.callPromising();',
    )


class _BrowserWorker:
    """
    `WorkerHandle` of `BrowserTransport.spawn()`: a cooperative task started
    with `.callPromising()`. A target that raises is logged, never re-raised
    into `join()`, like `threading.Thread`.
    """

    def __init__(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ):
        self._target = target
        self.name = name
        self.daemon = daemon
        self._done = False
        self._proxy = None
        self._promise = None

    def start(self) -> None:
        from pyodide.ffi import create_proxy

        handle = self

        def wrapped():
            token = _current_worker.set(handle)
            try:
                handle._target()
            except BaseException:
                import traceback

                traceback.print_exc()
            finally:
                _current_worker.reset(token)
                handle._done = True
                handle._proxy.destroy()

        self._proxy = create_proxy(wrapped)
        js_spawn = _get_js_spawn_fn()
        self._promise = js_spawn(self._proxy)

    def join(self, timeout: float | None = None) -> None:
        from pyodide.ffi import run_sync

        if self._promise is None or self._done:
            return

        _require_stack_switching('_BrowserWorker.join()')

        if timeout is None:
            run_sync(self._promise)
            return

        from js import Function

        # a timed-out join returns without raising, like Thread.join()
        race = Function.new(
            'promise',
            'timeoutMs',
            'return Promise.race(['
            'promise, '
            'new Promise((resolve) => setTimeout(resolve, timeoutMs)),'
            ']);',
        )
        run_sync(race(self._promise, timeout * 1000))

    def is_alive(self) -> bool:
        return self._promise is not None and not self._done


class BrowserTransport:
    """Transport backend for a pipeline running in a browser (Pyodide)"""

    # the telemetry manager puts batches of tuples on a queue, which a ring
    # does not accept: `Pipeline` leaves the telemetry off
    supports_telemetry = False

    def __init__(
        self,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
        max_meta_json_bytes: int = DEFAULT_MAX_META_JSON_BYTES,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    ):
        self._queue_capacity = queue_capacity
        self._max_meta_json_bytes = max_meta_json_bytes
        self._max_payload_bytes = max_payload_bytes

    def new_queue(self, maxsize: int = 0, local: bool = False) -> _BrowserQueue:
        # every queue is a ring, local or not; an unbounded queue (0) has no
        # equivalent here, and a larger maxsize is capped to the capacity
        # because it drives the memory pre-allocated
        capacity = (
            self._queue_capacity
            if not maxsize
            else min(maxsize, self._queue_capacity)
        )

        return _BrowserQueue(
            capacity=capacity,
            max_meta_json_bytes=self._max_meta_json_bytes,
            max_payload_bytes=self._max_payload_bytes,
        )

    def node_scope(self, shared: bool) -> contextlib.AbstractContextManager:
        return contextlib.nullcontext()

    def remote_destination(self, node_name: str) -> Any:
        raise ValueError(
            f'node {node_name} runs in another worker, which the '
            f'{type(self).__name__} transport cannot reach'
        )

    def new_event(self) -> _BrowserEvent:
        return _BrowserEvent()

    def new_lock(self) -> _BrowserLock:
        return _BrowserLock()

    def new_condition(self) -> _BrowserCondition:
        return _BrowserCondition()

    def spawn(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ) -> _BrowserWorker:
        return _BrowserWorker(target, name, daemon)

    def is_current(self, handle: WorkerHandle) -> bool:
        return _current_worker.get() is handle
