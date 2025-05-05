import json
import threading
import logging

from websockets.sync.client import connect

from juturna.components import Message
from juturna.components import BaseNode


class NotifierWebsocket(BaseNode):
    def __init__(self, endpoint: str):
        super().__init__('sink')

        self._endpoint = endpoint

        self._sent = 0
        self._t = None

    def warmup(self):
        logging.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message):
        message = message.to_dict()
        message['session_id'] = self.session_id

        self._t = threading.Thread(
            name='_post_transcript',
            target=self._send_message,
            args=(message,),
            daemon=True)

        self._t.start()

        self._sent += 1

    def _send_message(self, payload: dict):
        with connect(self._endpoint) as ws:
            try:
                ws.send(json.dumps(payload))
            except Exception as e:
                logging.warning(e)

    def destroy(self):
        if self._t:
            self._t.join()
        ...
