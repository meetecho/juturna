"""
BrowserOutput

Sink node delivering every message it receives to the web page hosting the
pipeline, as ``{type: 'output', node, message}`` through ``postMessage``.
"""

from juturna.components import Node
from juturna.components import Message

from juturna.transport._browser_io import message_to_js


class BrowserOutput(Node[object, None]):
    """Hand the received messages over to the page."""

    def update(self, message: Message, **kwargs):  # noqa: D102
        from js import Object
        from js import postMessage
        from pyodide.ffi import to_js

        postMessage(
            to_js(
                {
                    'type': 'output',
                    'node': self.name,
                    'message': message_to_js(message),
                },
                dict_converter=Object.fromEntries,
            )
        )
