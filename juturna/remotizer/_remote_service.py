"""
gRPC Server endpoint that receives and deserializes ProtoEnvelopes
Supports all payload types: Audio, Image, Video, Bytes, Object, Batch
"""

import grpc
import logging
import queue
import argparse
import threading
import json
import time

from typing import Any
from concurrent import futures

from juturna.remotizer.utils import (
    deserialize_envelope,
    create_envelope,
    message_to_proto,
)

from juturna.components import Message, Node
from juturna.remotizer._remote_builder import _standalone_builder

# Import generated protobuf code
from generated.payloads_pb2 import (
    ProtoEnvelope,
)
from generated import messaging_service_pb2_grpc

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('remote_service')


# ============================================================================
# HELPER CLASSES
# ============================================================================


class DispatchingQueue:
    """
    Wrapper around a queue to act as a Node destination.
    Nodes expect destinations to have a 'put' method.
    """

    def __init__(self):
        self.q = queue.Queue()

    def put(self, message: Message):
        """Put message into the underlying queue"""
        self.q.put(message)

    def get(self, timeout: float = 1.0) -> Any:
        """Get message from the underlying queue"""
        return self.q.get(timeout=timeout)


class RequestContext:
    """Context for tracking individual requests"""

    def __init__(
        self,
        sender: str,
        request_id: str,
        correlation_id: str,
        timeout: float,
        response_type: str = None,
    ):
        self.sender = sender
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.future = futures.Future()
        self.timeout = timeout
        self.response_type = response_type
        self.created_at = time.time()

    def is_valid_response(self, message: Message | None) -> bool:
        """Check if the inner payload type matches the expected response type"""
        print(self.response_type, type(message))
        if self.response_type is None or message is None:
            return True
        return type(message.payload).__name__ == self.response_type

    def is_expired(self) -> bool:
        """Check if request has exceeded its timeout"""
        return (time.time() - self.created_at) > self.timeout

    def cancel(self, reason: str):
        """Cancel the request with a reason"""
        if not self.future.done():
            self.future.set_exception(TimeoutError(reason))

    def done(self) -> bool:
        """Check if the future is done"""
        return self.future.done()

    def set_result(self, result: Message | None):
        """Set the result of the future"""
        print(f'Setting result for {self.correlation_id}: {result}')
        if not self.future.done() and self.is_valid_response(result):
            self.future.set_result(result)

    def result(self, timeout: float = None) -> Any:
        """Get the result of the future, blocking until available or timeout"""
        return self.future.result(timeout)


# ============================================================================
# gRPC SERVICE IMPLEMENTATION
# ============================================================================


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """Implementation of the gRPC Messaging Service (Async/Concurrent)"""

    DEFAULT_TIMEOUT = 30.0
    MAX_TIMEOUT = 300.0
    CLEANUP_INTERVAL = 10.0  # Cleanup expired requests every 10 seconds

    def __init__(self, node: Node, remote_name: str):
        self.node = node
        self.remote_name = remote_name
        self.dispatching_queue = DispatchingQueue()
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
                        cid
                        for cid, ctx in self.pending_requests.items()
                        if ctx.is_expired()
                    ]

                    for cid in expired:
                        ctx = self.pending_requests.pop(cid)
                        ctx.cancel(f'Request expired after {ctx.timeout}s')
                        logger.warning(f'Cleaned up expired request: {cid}')

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
                correlation_id = message.meta.get('correlation_id')

                if not correlation_id:
                    logger.warning(
                        f'Received message from {message.creator} '
                        'but no correlation_id found in metadata. '
                        'skipping...'
                    )
                    continue

                # Find and resolve the future
                with self.requests_lock:
                    req_ctx = self.pending_requests.pop(correlation_id, None)

                if req_ctx:
                    req_ctx.future.set_result(message)  # sets only if not done
                else:
                    logger.warning(f'Unknown correlation_id: {correlation_id}')

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f'Error in dispatcher loop: {e}', exc_info=True)

        logger.info('Dispatcher loop shutting down')
        # self._shutdown_complete.set()

    def SendAndReceive(self, request: ProtoEnvelope, context):
        """Handle request-response pattern asynchronously"""
        correlation_id = None
        try:
            self._increment_stat('total_requests')

            envelope_dict = deserialize_envelope(request)
            request_message = envelope_dict['message']
            correlation_id = envelope_dict.get('correlation_id')
            sender = envelope_dict.get('sender')
            request_id = envelope_dict.get('id')

            if not correlation_id:
                raise ValueError('Missing correlation_id in request envelope')

            if not sender:
                raise ValueError('Missing sender in request envelope')

            timeout = request.ttl if request.ttl > 0 else self.DEFAULT_TIMEOUT
            timeout = min(timeout, self.MAX_TIMEOUT)

            request_context = RequestContext(
                correlation_id=correlation_id,
                timeout=timeout,
                sender=sender,
                request_id=request_id,
                response_type=envelope_dict.get('response_type', None),
            )

            with self.requests_lock:
                if correlation_id in self.pending_requests:
                    raise ValueError(
                        f'Duplicate correlation_id: {correlation_id}'
                    )
                self.pending_requests[correlation_id] = request_context

            # Inject correlation_id into message meta
            request_message.meta['correlation_id'] = correlation_id

            # Inject Configuration for the Node Wrapper
            if envelope_dict.get('configuration'):
                _configuration_to_be_applied = envelope_dict.get(
                    'configuration', {}
                )

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
                    self.pending_requests.pop(correlation_id, None)

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
                response_to=request_id,
                timeout=timeout,
                correlation_id=correlation_id,
                id=correlation_id,  # ID of this response envelope
            )

            self._increment_stat('successful_requests')

            return response_envelope

        except TimeoutError as e:
            self._increment_stat('timeout_requests')
            logger.error(f'Timeout for {correlation_id}: {e}')
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


# ============================================================================
# SERVER STARTUP
# ============================================================================


def serve():
    parser = argparse.ArgumentParser(description='Juturna Remote Node Service')
    parser.add_argument(
        '--node-name', required=True, help='Name of the node to run'
    )
    parser.add_argument(
        '--node-mark', required=True, help='Mark of the node to run'
    )
    parser.add_argument(
        '--plugins-dir', required=True, help='Path to plugins directory'
    )
    parser.add_argument(
        '--pipe-name', default='warped_node', help='Pipeline name context'
    )
    parser.add_argument(
        '--port', type=int, default=50051, help='Port to listen on'
    )
    parser.add_argument(
        '--default-config',
        help='Default configuration as JSON string',
        default='{}',
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum number of worker threads',
    )

    args = parser.parse_args()

    try:
        default_config = json.loads(args.default_config)
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse default config: {e}')
        return

    logger.info(
        f"Building node '{args.node_name}' from '{args.plugins_dir}'..."
    )

    # We use _remote_builder.
    # Note: _remote_builder signature:
    #  - name,
    #  - plugins_dir,
    #  - context_runtime_path,
    #  - config=None
    # It returns (node, runtime_folder)

    try:
        node_instance, _ = _standalone_builder(
            name=args.node_name,
            plugins_dir=args.plugins_dir,
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


if __name__ == '__main__':
    serve()
