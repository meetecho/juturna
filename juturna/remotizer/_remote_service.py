"""
gRPC Server endpoint that receives and deserializes ProtoEnvelopes
Supports all payload types: Audio, Image, Video, Bytes, Object, Batch
"""

import grpc
import logging
import queue
import argparse
import threading
from concurrent import futures

from juturna.remotizer.utils import (
    deserialize_envelope,
    create_envelope,
    message_to_proto,
)

from juturna.components import Message, Node
from juturna.remotizer._remote_builder import _remote_builder

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


class ReceiverQueue:
    """
    Wrapper around a queue to act as a Node destination.
    Nodes expect destinations to have a 'put' method.
    """

    def __init__(self, q: queue.Queue):
        self.q = q

    def put(self, message: Message):
        """Put message into the underlying queue"""
        self.q.put(message)


# ============================================================================
# gRPC SERVICE IMPLEMENTATION
# ============================================================================


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """Implementation of the gRPC Messaging Service (Async/Concurrent)"""

    def __init__(self, node: Node):
        self.node = node

        # Queue for Node output
        self.output_queue = queue.Queue()

        # Attach to Node
        self.receiver = ReceiverQueue(self.output_queue)
        self.node.add_destination('remote_client_return', self.receiver)

        # Pending requests: correlation_id -> Future
        self.pending_requests: dict[str, futures.Future] = {}
        self.requests_lock = (
            threading.Lock()
        )  # Protects access to pending_requests dict

        # Start background dispatcher thread
        self._stop_event = threading.Event()
        self._dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop,
            name='RemoteServiceDispatcher',
            daemon=True,
        )
        self._dispatcher_thread.start()

        logger.info(f'Async Service initialized for node {node.name}')

    def _dispatcher_loop(self):
        """
        Background loop that reads from output_queue,
        and resolves pending futures.
        """
        while not self._stop_event.is_set():
            try:
                # Wait for a message from the Node
                message: Message = self.output_queue.get(timeout=1.0)

                # Check for correlation_id in metadata
                correlation_id = message.meta.get('correlation_id')

                if not correlation_id:
                    logger.warning(
                        f'Received message from {message.creator}',
                        'but no correlation_id found in metadata.',
                    )
                    continue

                # Find and resolve the future
                with self.requests_lock:
                    future = self.pending_requests.pop(correlation_id, None)

                if future:
                    if not future.done():
                        future.set_result(message)
                else:
                    logger.warning(
                        f'Received response for unknown correlation_id: {correlation_id}'  # noqa: E501
                    )

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f'Error in dispatcher loop: {e}', exc_info=True)

    def SendAndReceive(self, request: ProtoEnvelope, context):
        """Handle request-response pattern asynchronously"""
        try:
            # 1. Deserialize
            envelope_dict = deserialize_envelope(request)
            request_message = envelope_dict['message']

            # 2. Extract/Generate Correlation ID
            # The client SHOULD send a correlation_id in the envelope.
            # We map the envelope's correlation_id
            # (which might be the request_id from client perspective)
            # to our internal tracking.

            # Use the envelope's correlation_id or id if available
            cid = envelope_dict.get('correlation_id') or envelope_dict.get('id')

            if not cid:
                logger.warning(
                    'Request missing correlation_id',
                    'generating one but client might fail match.',
                )
                import uuid

                cid = str(uuid.uuid4())

            # 3. Prepare Future
            future = futures.Future()
            with self.requests_lock:
                self.pending_requests[cid] = future

            # 4. Inject Correlation ID into Message Meta
            # This is CRITICAL: The Node MUST propagate this metadata!
            request_message.meta['correlation_id'] = cid

            # 5. Inject into Node
            self.node.put(request_message)

            # 6. Wait for Future
            timeout = request.ttl if request.ttl > 0 else 30
            try:
                response_message = future.result(timeout=timeout)
            except futures.TimeoutError:
                # Cleanup
                with self.requests_lock:
                    self.pending_requests.pop(cid, None)

                logger.error(f'Node processing timed out for cid={cid}')
                context.abort(
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    'Node processing timed out',
                )
                return ProtoEnvelope()

            # 7. Serialize Response
            proto_response = message_to_proto(response_message)

            response_envelope = create_envelope(
                message=proto_response,
                creator='remote_service',
                configuration={},
                metadata={},
                request_type=envelope_dict['response_type'],
                priority=0,
                timeout=30,
                response_type=envelope_dict['request_type'],
                correlation_id=cid,
                id=cid,  # ID of this response envelope
            )

            return response_envelope

        except Exception as e:
            logger.error(f'Error processing request: {e}', exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, str(e))
            return ProtoEnvelope()


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
        '--pipe-name', default='remote_pipe', help='Pipeline name context'
    )
    parser.add_argument(
        '--port', type=int, default=50051, help='Port to listen on'
    )
    parser.add_argument(
        '--config',
        help='Optional configuration string (JSON/TOML) - placeholder for now',
    )  # Simplification

    args = parser.parse_args()

    # 1. Build the node
    logger.info(f"Building node '{args.node_name}'...")

    # We use _remote_builder.
    # Note: _remote_builder signature:
    #  - name,
    #  - plugins_dir,
    #  - context_runtime_path,
    #  - config=None
    # It returns (node, runtime_folder)

    try:
        node_instance, _ = _remote_builder(
            name=args.node_name,
            plugins_dir=args.plugins_dir,
            node_mark=args.node_mark,
            context_runtime_path=args.pipe_name,
            config={},
        )

        if node_instance is None:
            logger.error('Failed to build node.')
            return

        logger.info(f"Node '{node_instance.name}' built successfully.")

    except Exception as e:
        logger.error(f'Failed to instantiate node: {e}', exc_info=True)
        return

    # 2. Start gRPC Server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
        ],
    )

    messaging_service_pb2_grpc.add_MessagingServiceServicer_to_server(
        MessagingServiceImpl(node_instance), server
    )

    server.add_insecure_port(f'[::]:{args.port}')

    logger.info(f'Starting gRPC server on port {args.port}')
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info('Shutting down server...')
        node_instance.stop()
        server.stop(0)


if __name__ == '__main__':
    serve()
