"""
NotifierMongo

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com

Transmit messages to a Mongo endpoint.
"""

import pymongo

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import ObjectPayload


class NotifierMongo(Node[ObjectPayload, None]):
    """Node implementation class"""

    def __init__(
        self,
        endpoint: str,
        database: str,
        collection: str,
        timeout: int,
        **kwargs,
    ):
        """
        Parameters
        ----------
        endpoint : str
            The full mongo endpoint.
        database : str
            The destination datablase.
        collection : str
            The destination collection.
        timeout : int
            The timeout before dropping a message transmission.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._database = database
        self._collection = collection
        self._timeout = timeout

        self._client: pymongo.MongoClient | None = None
        self._db: pymongo.database.Database | None = None

    def warmup(self):
        """Warmup the node"""
        self._client = pymongo.MongoClient(self._endpoint)
        self._db = self._client[self._database]
        self._cl = self._db[self._collection]

        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message[ObjectPayload]):
        """Receive a message, transmit a message"""
        message = message.to_dict()
        message['session_id'] = self.pipe_id

        with pymongo.timeout(self._timeout):
            _ = self._cl.insert_one(message)

            self.logger.info('message sent')

    def destroy(self):
        """Close the connection with mongo"""
        if self._client:
            self._client.close()
