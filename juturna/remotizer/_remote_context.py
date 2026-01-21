from juturna.components import Message
from concurrent import futures
from typing import Any
import time


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
        if not self.future.done() and self.is_valid_response(result):
            self.future.set_result(result)

    def result(self, timeout: float = None) -> Any:
        """Get the result of the future, blocking until available or timeout"""
        return self.future.result(timeout)
