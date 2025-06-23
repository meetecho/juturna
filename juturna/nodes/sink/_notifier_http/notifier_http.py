import threading
import logging

import requests

from juturna.components import Message
from juturna.components import BaseNode


class NotifierHTTP(BaseNode):
    _CNT_CB = {
        'application/json': lambda m: m.to_dict(),
        'text/plain': lambda m: m.to_json()
    }

    def __init__(self, endpoint: str, timeout: int, content_type: str):
        super().__init__('sink')

        self._endpoint = endpoint
        self._timeout = timeout
        self._content_type = content_type

    @property
    def configuration(self) -> dict:
        base_config = super().configuration
        base_config['endpoint'] = self._endpoint

        return base_config

    def warmup(self):
        logging.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def set_on_config(self, property: str, value: str):
        if property == 'endpoint':
            logging.info(f'{self.name}: updating endpoint to {value}')

            self._endpoint = value

    def update(self, message: Message):
        message.meta['session_id'] = self.pipe_id
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

            logging.info('message sent')
            logging.info(f'  --> {response.status_code} - {response.text}')
        except Exception as e:
            logging.info(e)
