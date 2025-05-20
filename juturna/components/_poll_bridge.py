import copy
import time
import logging

from juturna.components._bridge import Bridge
from juturna.components._buffer import Buffer


class PollBridge(Bridge):
    def __init__(self, bridge_id: str):
        super().__init__(bridge_id)

        self._polling_version = None

    def _worker(self):
        if not isinstance(self.source, Buffer):
            raise TypeError(
                f'polling source must be a Buffer, not {type(self.source)}')

        if self.source:
            self._polling_version = self.source.version()

        while not self._stop_event.is_set():
            if self._mode == 'pre':
                time.sleep(self._sleep)

            if self.source is None:
                logging.warning(f'no source set for bridge {self.bridge_id}')
                return

            new_version = copy.deepcopy(self.source.version())

            if new_version != self._polling_version:
                self._polling_version = new_version

                if self._stop_event.is_set():
                    return

                if self._update_callback:
                    self._update_callback(
                        copy.deepcopy(self.source.data()))
                else:
                    logging.warning(
                        f'no callback set for bridge {self.bridge_id}')

            if self._mode == 'post':
                time.sleep(self._sleep)
