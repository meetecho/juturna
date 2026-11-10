import functools
import json
import signal
import threading
import time
import itertools

from collections import OrderedDict

from concurrent import futures

import grpc

from juturna.components import Message, Node, State
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

# requests accepted at once for each worker thread, when not set explicitly
REQUESTS_PER_WORKER = 10


class UnknownClientError(LookupError):
    """A sticky client sent no state, and the service has none for it"""


class DataLossError(RuntimeError):
    """In strict mode, part of what the node produced cannot reach a client"""


class InvalidRequestError(ValueError):
    """The request cannot be read, or lacks what the service needs"""


class TooManyClientsError(RuntimeError):
    """The service already keeps as many client states as it is allowed to"""


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """
    Implementation of the gRPC Messaging Service (Async/Concurrent)

    One node can serve several client pipelines at once. Each client warp node
    is identified by ``(pipe_id, sender)``, and is served in one of two ways:

    - sticky (the default): the client always reaches this service, which
      keeps its state and returns a copy of it with every response. The
      client sends its copy only when the service does not know it, after a
      restart or once its state was dropped for being idle, and the service
      starts again from that copy;
    - stateless: the client may reach any replica behind a balancer, so the
      state travels with every request, is used for that request only and
      returned with the response.

    The node is never re-linked to a state: each message is processed with
    the state of the request it belongs to, picked when the node's update
    thread gets to it. A request is answered when ``update()`` returns, with
    the first message it transmitted from the update thread, or with no
    message at all.

    Messages and states travel with their exact types. What cannot reach the
    client (a value that cannot be sent, a second message transmitted by one
    update, a message transmitted after its update returned or by another
    thread) is left out, with a warning the first time for each client. In
    strict mode it fails the request with DATA_LOSS instead, every time: for
    a message transmitted late, the next request of its client.

    A message transmitted outside ``update()`` never answers a request. Its
    client is the one of the last message processed only while the node is
    idle; when another message is being processed, the client cannot be
    told, and the loss is logged as an error.
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT = 300.0
    CLEANUP_INTERVAL = 10.0
    STATE_IDLE_TIMEOUT = 3600.0
    MAX_WARNED_CLIENTS = 1024
    DEFAULT_MAX_CLIENTS = 1024

    def __init__(
        self,
        node: Node,
        remote_name: str,
        strict: bool = False,
        max_clients: int = DEFAULT_MAX_CLIENTS,
    ):
        self.node = node
        self.remote_name = remote_name
        self.strict = strict
        self.max_clients = max_clients
        self._tracking_id_counter = itertools.count(start=1)

        self.node.add_destination('grpc_messaging_service', self)

        # tracking id -> request, also used to find the state of a message
        self.pending_requests: dict[int, RequestContext] = {}
        self.requests_lock = threading.RLock()

        # tracking id of the message inside update(), and the thread running
        # it: only that thread can transmit the output of that request
        self._current: tuple[int, int] | None = None

        self._state_store: dict[tuple[str, str], State] = {}
        self._state_last_used: dict[tuple[str, str], float] = {}
        self._state_lock = threading.Lock()
        self._ignored_configuration: set[tuple[str, str]] = set()
        self._warned: set[tuple] = set()

        # tracking id -> client of the requests already answered, to tell a
        # client about a message transmitted after its update returned
        self._answered: OrderedDict[int, tuple[str, str]] = OrderedDict()
        self._late_outputs: dict[tuple[str, str], str] = {}

        self._stop_event = threading.Event()

        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'invalid_requests': 0,
            'timeout_requests': 0,
            'unknown_client_requests': 0,
            'data_loss_requests': 0,
            'refused_requests': 0,
        }

        self.stats_lock = threading.Lock()

        self.node.link_state_resolver(self._resolve_state)
        self.node.link_update_observer(self._update_done)

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
        Messages of a request that is gone (timed out, cancelled by its
        client or on shutdown) are skipped, since nobody is waiting for
        their result. So is a message the service did not queue itself, such
        as one produced by a source of the node: it belongs to no client.
        """
        with self.requests_lock:
            self._current = None
            request = self.pending_requests.get(message.id)

            # tracking ids and the ids of other messages can be the same
            if request is not None and request.message is not message:
                request = None

        if request is None:
            logger.warning(
                f'request for message {message.id} is gone, skipping it'
            )

            return Node.SKIP_UPDATE

        if request.state is not None:
            state = request.state
        else:
            with self._state_lock:
                state = self._state_store.get(
                    request.state_key, Node.SKIP_UPDATE
                )

        if state is not Node.SKIP_UPDATE:
            with self.requests_lock:
                self._current = (message.id, threading.get_ident())

        return state

    def put(self, message: Message):
        """
        Collect a message transmitted by the node.

        The service is a destination of the node. A message transmitted by
        the update thread, inside ``update()``, is kept on the request being
        processed, which is answered once ``update()`` returns. Only the
        first message of a request is kept.

        Any other message was transmitted after its update returned, or by
        another thread of the node, and is never given to a request: the
        request being processed at that moment may belong to another client.
        """
        with self.requests_lock:
            current = self._current
            in_update = (
                current is not None and current[1] == threading.get_ident()
            )

            if in_update:
                tracking_id = current[0]
                request = self.pending_requests.get(tracking_id)
                client = (
                    request.state_key
                    if request is not None
                    else self._answered.get(tracking_id)
                )
            else:
                request = None
                tracking_id = getattr(message, '_data_source_id', None)
                # transmit() stamps the id of the last message processed:
                # while another one is in update(), that says nothing about
                # the client this message was made for
                client = (
                    self._answered.get(tracking_id) if current is None else None
                )

        if in_update and request is None:
            self._lose(
                client,
                'late message',
                f'a message transmitted for message {tracking_id} after its '
                'request was given up',
            )
        elif not in_update and current is not None:
            self._lose(
                None,
                'foreign message',
                'a message transmitted by another thread while message '
                f'{current[0]} was being processed',
            )
        elif not in_update:
            self._lose(
                client,
                'late message',
                f'a message transmitted for message {tracking_id} after its '
                'update returned',
            )
        elif request.output is None:
            request.output = message
        else:
            self._lose(
                client,
                'second message',
                f'a second message transmitted for message {tracking_id}',
                request,
            )

    def _lose(
        self,
        client: tuple[str, str] | None,
        kind: str,
        what: str,
        request: RequestContext | None = None,
    ):
        """Drop what cannot reach a client: warn, or fail in strict mode"""
        if not self.strict:
            self._warn_once(client, kind, f'{what} is lost')

            return

        if request is not None:
            request.data_loss = what
        elif client is not None:
            with self.requests_lock:
                # clients that never come back must not pile up here
                if (
                    client not in self._late_outputs
                    and len(self._late_outputs) >= self.MAX_WARNED_CLIENTS
                ):
                    del self._late_outputs[next(iter(self._late_outputs))]

                self._late_outputs[client] = what
        else:
            logger.error(f'{what} is lost, and its client is unknown')

    def _mark_answered(self, tracking_id: int, client: tuple[str, str]):
        # called with requests_lock held
        self._answered[tracking_id] = client

        if len(self._answered) > self.MAX_WARNED_CLIENTS:
            self._answered.popitem(last=False)

    def _warn_once(self, client: tuple[str, str] | None, kind: str, text: str):
        with self.requests_lock:
            if (client, kind) in self._warned:
                return

            if len(self._warned) >= self.MAX_WARNED_CLIENTS:
                self._warned.clear()

            self._warned.add((client, kind))

        sender, pipe_id = (client[1], client[0]) if client else ('?', '?')

        logger.warning(
            f'{text} (client {sender!r} of pipeline {pipe_id!r}; reported once)'
        )

    def _update_done(self, message: Message, error: Exception | None):
        # removed here, not once the response is sent: a message transmitted
        # in between must count as late, not as the output of the request
        with self.requests_lock:
            self._current = None
            request = self.pending_requests.pop(message.id, None)

            if request is not None:
                self._mark_answered(message.id, request.state_key)

        if request is None:
            return

        try:
            if error is not None:
                request.future.set_exception(
                    RuntimeError(f'Node update failed: {error}')
                )
            elif request.data_loss is not None:
                request.future.set_exception(
                    DataLossError(f'{request.data_loss} is lost')
                )
            else:
                request.future.set_result(request.output)
        except futures.InvalidStateError:
            logger.debug(f'request {message.id} already settled')

    def _seed_state(
        self, state_key: tuple[str, str], client_state: dict | None
    ):
        """
        Create the state of a client from its copy, if it is not known yet.

        Once created, the state here is the one the node updates, and the
        client copy only mirrors it through the response snapshots. A client
        copy sent later is not applied, or it could undo the changes made by
        requests the client has not seen the response of yet.

        Raises
        ------
        UnknownClientError
            If the client is not known and sent no copy.
        TooManyClientsError
            If the client is not known and the service keeps as many states
            as it is allowed to.

        """
        with self._state_lock:
            if state_key not in self._state_store:
                if client_state is None:
                    raise UnknownClientError(
                        f'unknown client {state_key[1]} of pipeline '
                        f'{state_key[0]}: send the state with the request'
                    )

                if len(self._state_store) >= self.max_clients:
                    raise TooManyClientsError(
                        f'the service already keeps the state of '
                        f'{self.max_clients} clients, and drops one after '
                        f'{self.STATE_IDLE_TIMEOUT:.0f}s without requests'
                    )

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
        if not config:
            return

        with self._state_lock:
            if state_key in self._ignored_configuration:
                return

            # stateless clients are never evicted, so the set is bounded here
            if len(self._ignored_configuration) >= self.MAX_WARNED_CLIENTS:
                self._ignored_configuration.clear()

            self._ignored_configuration.add(state_key)

        logger.warning(
            f'configuration sent by {state_key[1]!r} of pipeline '
            f'{state_key[0]!r} is ignored: the remote node is configured '
            'once, at startup, with --default-config'
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

    def _give_up(self, tracking_id: int, reason: str):
        """Stop waiting for a request: its message is skipped if still queued"""
        with self.requests_lock:
            request = self.pending_requests.pop(tracking_id, None)

            if request is not None:
                self._mark_answered(tracking_id, request.state_key)

        if request is not None:
            request.cancel(reason)

    def _read_request(self, request: ProtoEnvelope) -> dict:
        """
        Read the envelope of a request.

        Raises
        ------
        InvalidRequestError
            If the envelope cannot be read, or lacks what the service needs.

        """
        try:
            envelope_dict = deserialize_envelope(request)
        except (TypeError, ValueError) as e:
            raise InvalidRequestError(f'Malformed envelope: {e}') from e

        if not envelope_dict.get('sender') or not envelope_dict.get('pipe_id'):
            raise InvalidRequestError('Missing sender or pipe_id in envelope')

        if envelope_dict['message'] is None:
            raise InvalidRequestError('Missing message in envelope')

        client_state = envelope_dict['state']

        if client_state is not None and not isinstance(client_state, dict):
            raise InvalidRequestError('The state in the envelope is not a dict')

        if envelope_dict['stateless'] and client_state is None:
            raise InvalidRequestError('Missing state in a stateless request')

        return envelope_dict

    def SendAndReceive(self, request: ProtoEnvelope, context):
        """Handle request-response pattern asynchronously"""
        tracking_id = None

        try:
            self._increment_stat('total_requests')

            envelope_dict = self._read_request(request)
            request_message = envelope_dict['message']
            sender = envelope_dict['sender']
            envelope_id = envelope_dict.get('id')
            pipe_id = envelope_dict['pipe_id']

            state_key = (pipe_id, sender)
            stateless = envelope_dict['stateless']
            client_state = envelope_dict['state']

            if self.strict:
                with self.requests_lock:
                    late = self._late_outputs.pop(state_key, None)

                if late is not None:
                    raise DataLossError(
                        f'{late} is lost, so this message is not processed'
                    )

            if not stateless:
                self._seed_state(state_key, client_state)

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
                state=State(client_state) if stateless else None,
                message=request_message,
            )

            with self.requests_lock:
                self.pending_requests[tracking_id] = request_context

            # a client that cancels or disconnects is not waited for
            client_gone = functools.partial(
                self._give_up, tracking_id, 'Client gone'
            )

            if not context.add_callback(client_gone):
                client_gone()

            request_message.id = tracking_id
            request_message._freeze()
            self.node.put(request_message)

            try:
                response_message = request_context.future.result(timeout)
            except futures.TimeoutError as te:
                # raised by the wait, or with the reason the request was
                # given up for
                raise TimeoutError(
                    str(te) or f'Node processing timed out after {timeout}s'
                ) from te
            finally:
                # once removed, a message still queued is skipped by the node
                with self.requests_lock:
                    if self.pending_requests.pop(tracking_id, None) is not None:
                        self._mark_answered(tracking_id, state_key)

            response_state = (
                dict(request_context.state)
                if stateless
                else self._state_snapshot(state_key)
            )

            dropped = None if self.strict else list()

            try:
                response_proto = (
                    None
                    if response_message is None
                    else message_to_proto(response_message, dropped)
                )

                # a request message the node forwarded goes back under the
                # id its client gave it, not the tracking id
                if response_message is request_message:
                    response_proto.id = request_context.message_id

                response_envelope = create_envelope(
                    message=response_proto,
                    creator=self.remote_name,
                    pipe_id=pipe_id,
                    state=response_state,
                    configuration={},
                    metadata={
                        'processing_time': time.time()
                        - request_context.created_at
                    },
                    request_type=(
                        ''
                        if response_message is None
                        else type(response_message.payload).__name__
                    ),
                    priority=0,
                    response_to=envelope_id,
                    timeout=timeout,
                    stateless=stateless,
                    dropped=dropped,
                )
            except (TypeError, ValueError) as e:
                if self.strict:
                    raise DataLossError(str(e)) from e

                # not the fault of the request: never INVALID_ARGUMENT
                raise RuntimeError(f'The response cannot be sent: {e}') from e

            # once per client: paths holding keys or indices are always new
            if dropped:
                self._warn_once(
                    state_key,
                    'cannot be sent',
                    f'{", ".join(dropped)} cannot be sent, left out',
                )

            self._increment_stat('successful_requests')

            return response_envelope

        except DataLossError as e:
            self._increment_stat('data_loss_requests')
            logger.error(f'Data loss for {tracking_id}: {e}')
            context.abort(grpc.StatusCode.DATA_LOSS, str(e))
            return ProtoEnvelope()
        except UnknownClientError as e:
            self._increment_stat('unknown_client_requests')
            logger.info(str(e))
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
            return ProtoEnvelope()
        except TimeoutError as e:
            self._increment_stat('timeout_requests')
            logger.error(f'Timeout for {tracking_id}: {e}')
            context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, str(e))
            return ProtoEnvelope()
        except TooManyClientsError as e:
            self._increment_stat('refused_requests')
            logger.warning(f'Request refused: {e}')
            context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(e))
            return ProtoEnvelope()
        except InvalidRequestError as ve:
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


def serve(args) -> int:
    """
    Build the node and serve it until SIGINT or SIGTERM.

    Returns
    -------
    int
        The exit code of the command: 0 after a clean stop, 1 when the node
        cannot be built or the port cannot be used.

    """
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
            return 1

        logger.info(f"Node '{node_instance.name}' built successfully.")

    except Exception as e:
        logger.error(f'Failed to instantiate node: {e}', exc_info=True)
        return 1

    service_impl = MessagingServiceImpl(
        node_instance,
        remote_name=args.pipe_name,
        strict=args.strict,
        max_clients=args.max_clients,
    )

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=args.max_workers),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
            # a second service on the same port must fail, not share it
            ('grpc.so_reuseport', 0),
        ],
        # requests beyond this are refused, they do not queue in memory
        maximum_concurrent_rpcs=(
            args.max_requests or args.max_workers * REQUESTS_PER_WORKER
        ),
    )

    messaging_service_pb2_grpc.add_MessagingServiceServicer_to_server(
        service_impl,
        server,
    )

    try:
        bound_port = server.add_insecure_port(f'[::]:{args.port}')
    except RuntimeError as e:
        logger.error(f'Cannot listen on port {args.port}: {e}')
        bound_port = 0

    if not bound_port:
        service_impl.shutdown()
        node_instance.kill()
        node_instance.destroy()

        return 1

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

    return 0


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
