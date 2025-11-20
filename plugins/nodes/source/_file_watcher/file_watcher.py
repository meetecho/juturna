"""
FileWatcher

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2025-11-19 15:56:51

Watch a location on the filesystem, and fire desired events.

This is a source node, it however does not set a source function. Internally,
the node creates event handlers for the desired events to watch, and those
handlers write directly on the node inbound queue.
"""

import pathlib
import typing

from watchdog.events import FileSystemEvent
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from juturna.components import Node
from juturna.components import Message

from juturna.payloads._payloads import ObjectPayload


class FileWatcher(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        location: str,
        pattern: str,
        recursive: bool,
        ignore_directories: bool,
        ignore_updates: bool,
        ignore_deletions: bool,
        **kwargs,
    ):
        """
        Parameters
        ----------
        location : str
            Target location on the filesystem.
        pattern : str
            Glob-style pattern to apply when watching the target.
        recursive : bool
            If true, also watch subdirectories.
        ignore_directories : bool
            Do not watch for new directories.
        ignore_updates : bool
            Do not fire for updated files.
        ignore_deletions : bool
            Do not fire for deleted files
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._location = location
        self._handler = _Handler(
            self._queue,
            self.logger,
            ignore_directories=ignore_directories,
            ignore_updates=ignore_updates,
            ignore_deletions=ignore_deletions,
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
        message.version = self._sent
        message.creator = self.name

        self.transmit(message)

        self._sent += 1


class _Handler(PatternMatchingEventHandler):
    """File watcher for pattern matching"""

    def __init__(  # noqa
        self,
        q,
        logger,
        ignore_directories: bool,
        ignore_updates: bool,
        ignore_deletions: bool,
    ):
        super().__init__(ignore_directories=ignore_directories)
        self._q = q
        self._logger = logger

        self._ignore_updates = ignore_updates
        self._ignore_deletions = ignore_deletions

    def on_created(self, event: FileSystemEvent):
        """Catch creation events"""
        self._q.put(self._new_message(event))

    def on_deleted(self, event: FileSystemEvent):
        """Catch deletion events"""
        if not self._ignore_deletions:
            self._q.put(self._new_message(event))

    def on_modified(self, event: FileSystemEvent):
        """Catch update events"""
        if not self._ignore_updates:
            self._q.put(self._new_message(event))

    def _new_message(self, event: FileSystemEvent) -> Message[ObjectPayload]:
        evt = event.__dict__
        evt['src_path'] = pathlib.Path(evt['src_path']).resolve()

        return Message(payload=ObjectPayload.from_dict(evt))
