"""
ImageLoader

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com

Watch a location on the filesystem and load images when available.

This is a source node, it however does not set a source function. Internally,
the node creates event handlers for the desired events to watch, and those
handlers write directly on the node inbound queue.
"""

import pathlib
import typing
import time

import PIL
import numpy as np

from PIL import Image

from watchdog.events import FileSystemEvent
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import ImagePayload


class ImageLoader(Node[ObjectPayload, ImagePayload]):
    """Node implementation class"""

    def __init__(
        self,
        location: str,
        patterns: list,
        recursive: bool,
        ignore_updates: bool,
        convert_rgb: bool,
        **kwargs,
    ):
        """
        Parameters
        ----------
        location : str
            Target location on the filesystem.
        patterns : list
            Glob-style patterns to apply when watching the target.
        recursive : bool
            If true, also watch subdirectories.
        ignore_updates : bool
            Do not fire for updated files.
        convert_rgb : bool
            Force image format conversion into RGB.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._location = location
        self._patterns = patterns
        self._convert_rgb = convert_rgb

        self._handler = _Handler(
            self._queue,
            self.logger,
            ignore_updates=ignore_updates,
            patterns=patterns,
        )

        self._observer = Observer()
        self._observer.schedule(
            self._handler, self._location, recursive=recursive
        )

        self._sent = 0

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

        self._observer.start()

    def stop(self):
        """Stop the node"""
        # after custom stop code, invoke base node stop
        super().stop()

        self._observer.stop()
        self._observer.join()

    def destroy(self):
        """Destroy the node"""
        ...

    def update(self, message: Message[ObjectPayload]):
        """Receive data from upstream, transmit data downstream"""
        try:
            image = Image.open(message.payload['src_path'])

            if self._convert_rgb:
                image = image.convert('RGB')

            image.load()
        except PIL.UnidentifiedImageError:
            self.logger.warn(f'cannot load image {message.payload["src_path"]}')

            return

        image_arr = np.array(image)

        to_send = Message[ImagePayload](
            creator=self.name,
            version=self._sent,
            payload=ImagePayload(
                image=image_arr,
                width=image.width,
                height=image.height,
                depth=image_arr.shape[2],
                pixel_format=image.mode,
                timestamp=time.time(),
            ),
        )

        to_send.meta['src_path'] = message.payload['src_path']

        self.transmit(to_send)

        self._sent += 1


class _Handler(PatternMatchingEventHandler):
    """File watcher for pattern matching"""

    def __init__(  # noqa
        self, q, logger, ignore_updates: bool, patterns: list
    ):
        super().__init__(ignore_directories=True, patterns=patterns)
        self._q = q
        self._logger = logger

        self._ignore_updates = ignore_updates

    def on_created(self, event: FileSystemEvent):
        """Catch creation events"""
        self._q.put(self._new_message(event))

    def on_modified(self, event: FileSystemEvent):
        """Catch update events"""
        if not self._ignore_updates:
            self._q.put(self._new_message(event))

    def _new_message(self, event: FileSystemEvent) -> Message[ObjectPayload]:
        evt = event.__dict__
        evt['src_path'] = pathlib.Path(evt['src_path']).resolve()

        return Message(payload=ObjectPayload.from_dict(evt))
