import threading

import requests

from juturna.components import Message
from juturna.components import BaseNode

from juturna.payloads._payloads import ObjectPayload


class NotifierHTTP(BaseNode[ObjectPayload, None]):
    """Send data to a HTTP endpoint"""

    _CNT_CB = {
        'application/json': lambda m: m.to_dict(),
        'text/plain': lambda m: m.to_json()
    }

    def __init__(self,
                 endpoint: str,
                 timeout: int,
                 content_type: str,
                 **kwargs):
        """
        Parameters
        ----------
        endpoint : str
            Destination endpoint, including the port.
        timeout : int
            Transmission timeout.
        content_type : str
            Transmission data content type (this node supports, for now,
            application/json and text/plain data).
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._timeout = timeout
        self._content_type = content_type

    @property
    def configuration(self) -> dict:
        base_config = super().configuration
        base_config['endpoint'] = self._endpoint

        return base_config

    def warmup(self):
        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def set_on_config(self, property: str, value: str):
        if property == 'endpoint':
            self.logger.info(f'{self.name}: updating endpoint to {value}')

            self._endpoint = value

    def update(self, message: Message[ObjectPayload]):
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

            self.logger.info('message sent')
            self.logger.info(f'  --> {response.status_code} - {response.text}')
        except Exception as e:
            self.logger.info(e)
