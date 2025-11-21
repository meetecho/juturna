"""
gRPC Server endpoint that receives and deserializes ProtoEnvelopes
Supports all payload types: Audio, Image, Video, Bytes, Object, Batch
"""

import grpc
import numpy as np
import logging
from concurrent import futures
from typing import Any

from juturna.remotizer.utils import (
    deserialize_envelope,
    create_envelope,
    message_to_proto,
)

from juturna.components import Message
from juturna.payloads import (
    ObjectPayload,
)

# Import generated protobuf code
from generated.payloads_pb2 import (
    ProtoEnvelope,
)
from generated import messaging_service_pb2_grpc

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# MESSAGE HANDLER REGISTRY
# ============================================================================


class MessageHandler:
    """Registry for handling different message types"""

    def __init__(self): ...

    def handle(self, envelope_dict: dict[str, Any]) -> Any:
        """Route message to appropriate handler"""
        payload_type = envelope_dict['message']['payload_type']

        if payload_type not in self.handlers:
            logger.warning(f'No handler registered for {payload_type}')
            return None

        handler = self.handlers[payload_type]
        return handler(envelope_dict)


# ============================================================================
# gRPC SERVICE IMPLEMENTATION
# ============================================================================


class MessagingServiceImpl(messaging_service_pb2_grpc.MessagingServiceServicer):
    """Implementation of the gRPC Messaging Service"""

    def __init__(self):
        self.handler = MessageHandler()

    def SendMessage(self, request: ProtoEnvelope, context):
        """Handle incoming message and return acknowledgment"""
        try:
            # Log incoming message
            logger.info(f'Received envelope {request.id} from {request.sender}')

            # Deserialize the envelope
            envelope_dict = deserialize_envelope(request)

            # Log details
            logger.info(
                f'Message type: {envelope_dict["message"]["payload_type"]}'
            )
            logger.info(f'Creator: {envelope_dict["message"]["creator"]}')
            logger.info(f'Correlation ID: {envelope_dict["correlation_id"]}')

            # Handle the message
            result = self.handler.handle(envelope_dict)

        except Exception as e:
            logger.error(f'Error processing message: {e}', exc_info=True)

    def SendAndReceive(self, request: ProtoEnvelope, context):
        """Handle request-response pattern"""
        # Process the incoming message
        # Log incoming message
        logger.info(f'Received envelope {request.id} from {request.sender}')

        # Deserialize the envelope
        envelope_dict = deserialize_envelope(request)
        request_message = envelope_dict['message']

        # Log details
        logger.info(f'Message type: {envelope_dict["message"]["payload_type"]}')
        logger.info(f'Creator: {envelope_dict["message"]["creator"]}')
        logger.info(f'Correlation ID: {envelope_dict["correlation_id"]}')

        #        response_message = self.handler.handle(request_message)
        response_message = Message[ObjectPayload](
            creator='mock-creator',
            version=envelope_dict['message']['version'],
            payload=ObjectPayload.from_dict({'result': 'ok'}),
            timers_from=request_message.timers,
        )

        proto_response = message_to_proto(response_message)

        response_envelope = create_envelope(
            message=proto_response,
            creator='response_handler',
            request_type=envelope_dict['response_type'],
            priority=0,
            timeout=30,
            response_type=envelope_dict['request_type'],
            correlation_id=envelope_dict['id'],
            id=envelope_dict['correlation_id'],
        )
        return response_envelope

    # def StreamMessages(self, request_iterator, context):
    #     """Handle streaming messages"""
    #     for envelope in request_iterator:
    #         response = self.SendMessage(envelope, context)
    #         yield response


# ============================================================================
# SERVER STARTUP
# ============================================================================


def serve(port: int = 50051, max_workers: int = 10):
    """Start the gRPC server"""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
        ],
    )

    # Add the service
    messaging_service_pb2_grpc.add_MessagingServiceServicer_to_server(
        MessagingServiceImpl(), server
    )

    # Bind to port
    server.add_insecure_port(f'[::]:{port}')

    logger.info(f'Starting gRPC server on port {port}')
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info('Shutting down server...')
        server.stop(0)


if __name__ == '__main__':
    serve()
