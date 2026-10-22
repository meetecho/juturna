import json
import queue
import signal
import threading
import time
import itertools

from concurrent import futures

import grpc

from juturna.components import Message, Node, State
from juturna.payloads import Batch
from juturna.remotizer._remote_context import RequestContext
from juturna.remotizer._remote_builder import _standalone_builder

from juturna.remotizer.utils import (
    deserialize_envelope,
    create_envelope,
    message_to_proto,
)

from juturna.remotizer.c_protos.payloads_pb2 import ProtoEnvelope
from juturna.remotizer.c_protos import messaging_service_pb2_grpc

from juturna.utils.log_utils import jt_logger


logger = jt_logger('remote_service')


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """
    Implementation of the gRPC Messaging Service (Async/Concurrent)

    One node can serve several client pipelines at once. Each client warp node
    is identified by ``(pipe_id, sender)`` and has its own state here, created
    from the copy sent with its first request and returned to it as a
    snapshot with every response. The node is never re-linked to a state:
    each message is processed with the state of the request it belongs to,
    picked when the node's update thread gets to it.
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT = 300.0
    CLEANUP_INTERVAL = 10.0
    STATE_IDLE_TIMEOUT = 3600.0

    def __init__(self, node: Node, remote_name: str):
        self.node = node
        self.remote_name = remote_name
        self._tracking_id_counter = itertools.count(start=1)

        self.dispatching_queue = queue.Queue()
        self.node.add_destination(
            'grpc_messaging_service', self.dispatching_queue
        )

        # tracking id -> request, also used to find the state of a message
        self.pending_requests: dict[int, RequestContext] = {}
        self.requests_lock = threading.RLock()

        self._state_store: dict[tuple[str, str], State] = {}
        self._state_last_used: dict[tuple[str, str], float] = {}
        self._state_lock = threading.Lock()
        self._ignored_configuration: set[tuple[str, str]] = set()

        self._stop_event = threading.Event()

        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'invalid_requests': 0,
            'timeout_requests': 0,
        }

        self.stats_lock = threading.Lock()

        self.node.link_state_resolver(self._resolve_state)

        self._dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop,
            name='RemoteServiceDispatcher',
            daemon=True,
        )
        self._dispatcher_thread.start()

        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name='RemoteServiceCleanup',
            daemon=True,
        )
        self._cleanup_thread.start()

        logger.info(f'Service initialized for node {node.name}')

    def _increment_stat(self, stat_name: str):
        """Thread-safe statistics increment"""
        with self.stats_lock:
            self.stats[stat_name] = self.stats.get(stat_name, 0) + 1

    def _resolve_state(self, message: Message):
        """
        Return the state of the request a message belongs to.

        Called by the node's update thread for every message it processes.
        Messages of a request that is gone (timed out, or cancelled on
        shutdown) are skipped, since nobody is waiting for their result.
        """
        if isinstance(message.payload, Batch):
            ids = [m.id for m in message.payload.messages]
        else:
            ids = [message.id]

        with self.requests_lock:
            keys = {
                self.pending_requests[tracking_id].state_key
                for tracking_id in ids
                if tracking_id in self.pending_requests
            }

        if not keys:
            logger.warning(
                f'request for message {message.id} is gone, skipping it'
            )

            return Node.SKIP_UPDATE

        if len(keys) > 1:
            raise ValueError(
                f'batch {message.id} mixes messages of {sorted(keys)}, '
                'a shared remote node needs a passthrough synchroniser'
            )

        with self._state_lock:
            return self._state_store.get(keys.pop(), Node.SKIP_UPDATE)

    def _seed_state(self, state_key: tuple[str, str], client_state: dict):
        """
        Create the state of a client from its copy, if it is not known yet.

        Once created, the state here is the one the node updates, and the
        client copy only mirrors it through the response snapshots. A client
        copy sent later is not applied, or it could undo the changes made by
        requests the client has not seen the response of yet.
        """
        with self._state_lock:
            if state_key not in self._state_store:
                self._state_store[state_key] = State(client_state)

                logger.info(f'created state for {state_key}')

            self._state_last_used[state_key] = time.time()

    def _state_snapshot(self, state_key: tuple[str, str]) -> dict:
        with self._state_lock:
            state = self._state_store.get(state_key)

        # a plain dict copy, safe against the update thread writing to it
        return dict(state.data) if state is not None else dict()

    def _check_configuration(self, state_key: tuple[str, str], config: dict):
        # the node serves every client, so it is only configured at startup
        if not config or state_key in self._ignored_configuration:
            return

        self._ignored_configuration.add(state_key)

        logger.warning(
            f'configuration sent by {state_key[1]} of pipeline {state_key[0]} '
            'is ignored: the remote node is configured once, at startup, '
            'with --default-config'
        )

    def _evict_idle_states(self):
        now = time.time()

        with self.requests_lock:
            busy = {ctx.state_key for ctx in self.pending_requests.values()}

        with self._state_lock:
            idle = [
                key
                for key, last_used in self._state_last_used.items()
                if now - last_used > self.STATE_IDLE_TIMEOUT and key not in busy
            ]

            for key in idle:
                del self._state_store[key]
                del self._state_last_used[key]
                self._ignored_configuration.discard(key)

                logger.info(f'dropped idle state for {key}')

    def _cleanup_loop(self):
        """Background loop that periodically cleans up expired requests"""
        while not self._stop_event.wait(self.CLEANUP_INTERVAL):
            try:
                with self.requests_lock:
                    expired = [
                        tracking_id
                        for tracking_id, ctx in self.pending_requests.items()
                        if ctx.is_expired()
                    ]

                    for tracking_id in expired:
                        ctx = self.pending_requests.pop(tracking_id)
                        ctx.cancel(f'Request expired after {ctx.timeout}s')
                        logger.warning(
                            f'Cleaned up expired request: {tracking_id}'
                        )

                self._evict_idle_states()

            except Exception as e:
                logger.error(f'Error in cleanup loop: {e}', exc_info=True)

    def _dispatcher_loop(self):
        """
        Background loop that reads from output_queue,
        and resolves pending futures.
        """
        while not self._stop_event.is_set():
            try:
                message: Message = self.dispatching_queue.get(timeout=1.0)
                tracking_id = message._data_source_id

                if not tracking_id:
                    logger.warning(
                        f'Received message from {message.creator} '
                        'but no tracking_id found in response. '
                        'skipping...'
                    )
                    continue

                with self.requests_lock:
                    req_ctx = self.pending_requests.pop(tracking_id, None)

                if req_ctx and not req_ctx.done():
                    req_ctx.future.set_result(message)
                else:
                    logger.warning(f'Unknown tracking_id: {tracking_id}')

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f'Error in dispatcher loop: {e}', exc_info=True)

        logger.info('Dispatcher loop shutting down')

    def SendAndReceive(self, request: ProtoEnvelope, context):
        """Handle request-response pattern asynchronously"""
        tracking_id = None

        try:
            self._increment_stat('total_requests')

            envelope_dict = deserialize_envelope(request)
            request_message = envelope_dict['message']
            sender = envelope_dict.get('sender')
            envelope_id = envelope_dict.get('id')
            pipe_id = envelope_dict.get('pipe_id')

            if not sender or not pipe_id:
                raise ValueError('Missing sender or pipe_id in envelope')

            state_key = (pipe_id, sender)

            self._seed_state(state_key, envelope_dict.get('state') or dict())
            self._check_configuration(
                state_key, envelope_dict.get('configuration')
            )

            timeout = request.ttl if request.ttl > 0 else self.DEFAULT_TIMEOUT
            timeout = min(timeout, self.MAX_TIMEOUT)

            tracking_id = next(self._tracking_id_counter)
            request_context = RequestContext(
                message_id=request_message.id,
                timeout=timeout,
                sender=sender,
                envelope_id=envelope_id,
                response_type=envelope_dict.get('response_type', None),
                state_key=state_key,
            )

            with self.requests_lock:
                self.pending_requests[tracking_id] = request_context

            request_message.id = tracking_id
            request_message._freeze()
            self.node.put(request_message)

            try:
                response_message = request_context.future.result(timeout)
            except futures.TimeoutError as te:  # a different TimeoutError
                raise TimeoutError(
                    f'Node processing timed out after {timeout}s'
                ) from te
            finally:
                # once removed, a message still queued is skipped by the node
                with self.requests_lock:
                    self.pending_requests.pop(tracking_id, None)

            proto_response = message_to_proto(response_message)

            response_envelope = create_envelope(
                message=proto_response,
                creator=self.remote_name,
                pipe_id=pipe_id,
                state=self._state_snapshot(state_key),
                configuration={},
                metadata={
                    'processing_time': time.time() - request_context.created_at
                },
                request_type=type(response_message.payload).__name__,
                priority=0,
                response_to=envelope_id,
                timeout=timeout,
            )

            self._increment_stat('successful_requests')

            return response_envelope

        except TimeoutError as e:
            self._increment_stat('timeout_requests')
            logger.error(f'Timeout for {tracking_id}: {e}')
            context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, str(e))
            return ProtoEnvelope()
        except ValueError as ve:
            self._increment_stat('invalid_requests')
            logger.error(f'Invalid request: {ve}')
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(ve))
            return ProtoEnvelope()
        except Exception as e:
            self._increment_stat('failed_requests')
            logger.error(f'Error processing request: {e}', exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, str(e))
            return ProtoEnvelope()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info('Initiating service shutdown...')
        self._stop_event.set()
        self._dispatcher_thread.join(timeout=5.0)
        self._cleanup_thread.join(timeout=5.0)

        with self.requests_lock:
            for _, ctx in self.pending_requests.items():
                ctx.cancel('Service shutting down')
            self.pending_requests.clear()

        with self._state_lock:
            self._state_store.clear()
            self._state_last_used.clear()

        # Log final statistics
        with self.stats_lock:
            logger.info(f'Final statistics: {self.stats}')

        logger.info('Service shutdown complete')

    def get_stats(self) -> dict[str, int]:
        """Get current statistics"""
        with self.stats_lock:
            return self.stats.copy()


def serve(args):
    jt_logger().setLevel(args.log_level)

    if args.default_config:
        with open(args.default_config) as f:
            default_config = json.load(f)
    else:
        default_config = dict()

    logger.info(f"Building node '{args.node_name}' ({args.node_type}) ...")

    try:
        node_instance, _ = _standalone_builder(
            name=args.node_name,
            node_type=args.node_type,
            context_runtime_path=args.pipe_name,
            config=default_config.copy(),
        )

        if node_instance is None:
            logger.error('Failed to build node.')
            return

        logger.info(f"Node '{node_instance.name}' built successfully.")

    except Exception as e:
        logger.error(f'Failed to instantiate node: {e}', exc_info=True)
        return

    service_impl = MessagingServiceImpl(
        node_instance, remote_name=args.pipe_name
    )

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=args.max_workers),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
        ],
    )

    messaging_service_pb2_grpc.add_MessagingServiceServicer_to_server(
        service_impl,
        server,
    )

    server.add_insecure_port(f'[::]:{args.port}')

    stop_requested = threading.Event()

    def _request_stop(signum, _frame):
        logger.info(f'received {signal.Signals(signum).name}, stopping...')
        stop_requested.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, _request_stop)

    logger.info(f'Starting gRPC server on port {args.port}')
    server.start()

    while not stop_requested.wait(1.0):
        pass

    shutdown(server, service_impl, node_instance)


def shutdown(server, service_impl: MessagingServiceImpl, node: Node):
    """
    Stop the service and release the node.

    New requests are refused first and the ones in progress get a grace
    period; whatever is still pending after that is cancelled. The node is
    then killed (a hung update() cannot block the shutdown) and destroyed, so
    that its resources are released.
    """
    server.stop(grace=5.0).wait()
    service_impl.shutdown()

    node.kill()
    node.destroy()

    logger.info('gRPC server stopped gracefully')
