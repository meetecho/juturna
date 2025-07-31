import copy
import threading
import logging

from juturna.components import Message
from juturna.components._bridge import Bridge
from juturna.components._buffer import Buffer


class PollBridge(Bridge):
    def __init__(self, bridge_id: str):
        super().__init__(bridge_id)

        self._latest_message = None
        self._ready = threading.Event()

    def _on_buffer_update(self, message: Message) -> None:
        self._latest_message = message
        self._ready.set()

    def _worker(self):
        while not self._stop_event.is_set():
            self._ready.wait()
            self._ready.clear()

            if self._update_callback:
                self._update_callback(copy.deepcopy(self._latest_message))
            else:
                logging.warning(
                    f'no callback set for bridge {self.bridge_id}')