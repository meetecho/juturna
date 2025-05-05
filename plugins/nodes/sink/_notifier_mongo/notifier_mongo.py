import threading
import logging

import pymongo

from juturna.components import Message
from juturna.components import BaseNode


class NotifierMongo(BaseNode):
    def __init__(self, endpoint: str, database: str, collection: str):
        super().__init__('sink')

        self._endpoint = endpoint
        self._database = database
        self._collection = collection

        self._sent = 0
        self._t = None

    def warmup(self):
        logging.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message):
        message = message.to_dict()
        message['session_id'] = self.session_id

        self._t = threading.Thread(
            name='_notify_mongo',
            target=self._send_message,
            args=(message,),
            daemon=True)

        self._t.start()

        self._sent += 1

    def _send_message(self, payload: dict):
        with pymongo.MongoClient(self._endpoint) as client:
            try:
                target_cl = client[self._database][self._collection]
                _ = target_cl.insert_one(payload)
            except Exception as e:
                logging.info(e)

    def destroy(self):
        if self._t:
            self._t.join()
