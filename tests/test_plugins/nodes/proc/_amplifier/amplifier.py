"""
Amplifier

@author: not provided
@email: not provided
@created_at: 2026-01-08 17:18:37

Automatically generated with jt.utils.node_utils.node_stub
"""
import typing

from juturna.components import Node
from juturna.components import Message

# BasePayload type is intended to be a placehoder for the input-output types
# you intend to use in the node implementation
from juturna.payloads._payloads import BasePayload


class Amplifier(Node[BasePayload, BasePayload]):
    """Node implementation class"""

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

    def configure(self):
        """Configure the node"""
        ...

    def warmup(self):
        """Warmup the node"""
        ...

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        ...

    def start(self):
        """Start the node"""
        # after custom start code, invoke base node start
        super().start()

    def stop(self):
        """Stop the node"""
        # after custom stop code, invoke base node stop
        super().stop()

    def destroy(self):
        """Destroy the node"""
        ...

    def update(self, message: Message[BasePayload]):
        """Receive data from upstream, transmit data downstream"""
        ...

    # uncomment next_batch to design custom synchronisation policy
    # def next_batch(sources: dict) -> dict:
    #     ...
