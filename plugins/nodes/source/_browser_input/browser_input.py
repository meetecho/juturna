"""
BrowserInput

Source node fed by the web page hosting the pipeline.

It sets no source function: the host calls ``feed()`` with a message in the
wire format of ``juturna.transport._browser_io`` and the node puts it on its
own queue, like ``file_watcher`` does with filesystem events.
"""

from juturna.components import Node
from juturna.components import Message

from juturna.transport._browser_io import message_from_js


class BrowserInput(Node[object, object]):
    """Forward the messages handed over by the page to the pipeline."""

    def feed(self, js_message):
        """
        Put a message coming from the page on the node queue.

        Blocks when the queue is full, so it must be invoked through
        ``.callPromising()``.

        Parameters
        ----------
        js_message : JsProxy
            A JS object ``{kind, payload, meta}``.

        Raises
        ------
        ValueError
            If the message kind or its payload fields are not valid.

        """
        self.put(message_from_js(js_message, self.name))

    def update(self, message: Message, **kwargs):  # noqa: D102
        self.transmit(message)
