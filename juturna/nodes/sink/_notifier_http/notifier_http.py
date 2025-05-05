import threading
import logging

import requests

from juturna.components import Message
from juturna.components import BaseNode


class NotifierHTTP(BaseNode):
    _CNT_CB = {
        'application/json': lambda m: m.to_dict(),
        'application/text': lambda m: m.to_json()
    }

    def __init__(self, endpoint: str, timeout: int, content_type: str):
        super().__init__('sink')

        self._endpoint = endpoint
        self._timeout = timeout
        self._content_type = content_type

    def warmup(self):
        logging.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message):
        message.meta['session_id'] = self.session_id
        message = NotifierHTTP._CNT_CB[self._content_type](message)

        t = threading.Thread(
            name=f'{self.name}_thread',
            target=self._send_chunk,
            args=(message,),
            daemon=True)

        t.start()

    def _send_chunk(self, message_cnt):
        try:
            headers = { 'Content-Type': self._content_type }
            response = requests.post(
                self._endpoint,
                json=message_cnt,
                headers=headers,
                timeout=self._timeout)

            logging.info(f'message sent - result: {response.status_code} - {response.text}')
        except Exception as e:
            logging.info(e)
