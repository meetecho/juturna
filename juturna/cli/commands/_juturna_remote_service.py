import json
import logging
import queue
import threading
import time
import itertools

from concurrent import futures

import grpc

from juturna.components import Message, Node
from juturna.remotizer._remote_context import RequestContext
from juturna.remotizer._remote_builder import _standalone_builder

from juturna.remotizer.utils import (
    deserialize_envelope,
    create_envelope,
    message_to_proto,
)

from juturna.remotizer.c_protos.payloads_pb2 import ProtoEnvelope
from juturna.remotizer.c_protos import messaging_service_pb2_grpc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('remote_service')


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """Implementation of the gRPC Messaging Service (Async/Concurrent)"""

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT = 300.0
    CLEANUP_INTERVAL = 10.0

    def __init__(self, node: Node, remote_name: str):
        self.node = node
        self.remote_name = remote_name
        self._tracking_id_counter = itertools.count(start=1)

        self.dispatching_queue = queue.Queue()
        self.node.add_destination(
            'grpc_messaging_service', self.dispatching_queue
        )

        self.pending_requests: dict[str, RequestContext] = {}
        self.requests_lock = threading.RLock()

        self._stop_event = threading.Event()
        self._shutdown_event = threading.Event()

        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'timeouts': 0,
        }

        self.stats_lock = threading.Lock()

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

    def _cleanup_loop(self):
        """Background loop that periodically cleans up expired requests"""
        while not self._stop_event.is_set():
            try:
                time.sleep(self.CLEANUP_INTERVAL)

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
                if req_ctx:
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
        try:
            self._increment_stat('total_requests')

            envelope_dict = deserialize_envelope(request)
            request_message = envelope_dict['message']
            tracking_id = next(self._tracking_id_counter)
            sender = envelope_dict.get('sender')
            envelope_id = envelope_dict.get('id')

            if not sender:
                raise ValueError('Missing sender in request envelope')

            timeout = request.ttl if request.ttl > 0 else self.DEFAULT_TIMEOUT
            timeout = min(timeout, self.MAX_TIMEOUT)

            request_context = RequestContext(
                message_id=request_message.id,
                timeout=timeout,
                sender=sender,
                envelope_id=envelope_id,
                response_type=envelope_dict.get('response_type', None),
            )

            with self.requests_lock:
                if tracking_id in self.pending_requests:
                    raise ValueError(f'Duplicate tracking_id: {tracking_id}')
                self.pending_requests[tracking_id] = request_context

            request_message.id = tracking_id

            if envelope_dict.get('configuration'):
                _configuration_to_be_applied = envelope_dict.get(
                    'configuration', {}
                )

            request_message._freeze()
            self.node.put(request_message)

            try:
                response_message = request_context.future.result(timeout)
            except futures.TimeoutError as te:  # a different TimeoutError
                raise TimeoutError(
                    f'Node processing timed out after {timeout}s'
                ) from te
            except Exception:
                raise
            finally:
                with self.requests_lock:
                    self.pending_requests.pop(tracking_id, None)

            proto_response = message_to_proto(response_message)

            response_envelope = create_envelope(
                message=proto_response,
                creator=self.remote_name,
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

        # Log final statistics
        with self.stats_lock:
            logger.info(f'Final statistics: {self.stats}')

        logger.info('Service shutdown complete')

    def get_stats(self) -> dict[str, int]:
        """Get current statistics"""
        with self.stats_lock:
            return self.stats.copy()


def serve(args):
    if args.default_config:
        with open(args.default_config) as f:
            default_config = json.load(f)
    else:
        default_config = dict()

    logger.info(f"Building node '{args.node_name}' from '{args.plugin_dir}'...")

    try:
        node_instance, _ = _standalone_builder(
            name=args.node_name,
            plugin_dir=args.plugin_dir,
            node_mark=args.node_mark,
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

    logger.info(f'Starting gRPC server on port {args.port}')
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        service_impl.shutdown()
        node_instance.stop()
        server.stop(grace=5.0)
        logger.info('gRPC server stopped gracefully')
