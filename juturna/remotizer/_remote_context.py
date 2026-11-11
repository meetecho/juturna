from juturna.components import Message, State
from concurrent import futures
import contextlib
from typing import Any
import time


class RequestContext:
    """Context for tracking individual requests"""

    def __init__(
        self,
        sender: str,
        envelope_id: str,
        message_id: int,
        timeout: float,
        state_key: tuple[str, str, str] | None = None,
        state: State | None = None,
        message: Message | None = None,
    ):
        self.sender = sender
        self.envelope_id = envelope_id
        self.message_id = message_id
        self.future = futures.Future()
        self.timeout = timeout
        self.state_key = state_key
        # set for a stateless client only, otherwise the state is in the store
        self.state = state
        # the message queued on the node for this request
        self.message = message
        self.output: Message | None = None
        # what the update produced that cannot reach the client, strict mode
        self.data_loss: str | None = None
        self.created_at = time.time()

    def is_expired(self) -> bool:
        """Check if request has exceeded its timeout"""
        return (time.time() - self.created_at) > self.timeout

    def cancel(self, reason: str):
        """Cancel the request with a reason"""
        # the node may settle it at the same time
        with contextlib.suppress(futures.InvalidStateError):
            self.future.set_exception(TimeoutError(reason))

    def done(self) -> bool:
        """Check if the future is done"""
        return self.future.done()

    def set_result(self, result: Message | None):
        """Set the result of the future"""
        if not self.future.done():
            self.future.set_result(result)

    def result(self, timeout: float = None) -> Any:
        """Get the result of the future, blocking until available or timeout"""
        return self.future.result(timeout)
