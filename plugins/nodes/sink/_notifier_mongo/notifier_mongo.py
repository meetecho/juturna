"""
NotifierMongo

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com

Transmit messages to a Mongo endpoint.
"""

import threading

import pymongo

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import ObjectPayload


class NotifierMongo(Node[ObjectPayload, None]):
    """Node implementation class"""

    def __init__(self, endpoint: str, database: str, collection: str):
        """
        Parameters
        ----------
        endpoint : str
            The full mongo endpoint.
        database : str
            The destination datablase.
        collection : str
            The destination collection.

        """
        super().__init__('sink')

        self._endpoint = endpoint
        self._database = database
        self._collection = collection

        self._sent = 0
        self._t = None

    def warmup(self):
        """Warmup the node"""
        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message[ObjectPayload]):
        """Receive a message, transmit a message"""
        message = message.to_dict()
        message['session_id'] = self.pipe_id

        self._t = threading.Thread(
            name='_notify_mongo',
            target=self._send_message,
            args=(message,),
            daemon=True,
        )

        self._t.start()

        self._sent += 1

    def _send_message(self, payload: dict):
        with pymongo.MongoClient(self._endpoint) as client:
            try:
                target_cl = client[self._database][self._collection]
                _ = target_cl.insert_one(payload)
            except Exception as e:
                self.logger.info(e)

    def destroy(self):
        """Destroy the node"""
        if self._t:
            self._t.join()
