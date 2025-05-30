import copy
import time
import typing
import logging

from juturna.components._bridge import Bridge


class StreamBridge(Bridge):
    def __init__(self, bridge_id: str):
        super().__init__(bridge_id)

    def _worker(self):
        if not isinstance(self.source, typing.Callable):
            raise TypeError(
                f'streaming source must be a Callable, not {type(self.source)}')

        while not self._stop_event.is_set():
            if self._mode == 'pre':
                time.sleep(self._sleep)

            if self.source is None:
                logging.warning(f'no source set for bridge {self.bridge_id}')
                return

            incoming_data = self.source()

            if self._stop_event.is_set():
                return

            if self._update_callback:
                self._update_callback(copy.deepcopy(incoming_data))
            else:
                logging.warning(
                    f'no callback set for bridge {self.bridge_id}')

            if self._mode == 'post':
                time.sleep(self._sleep)
