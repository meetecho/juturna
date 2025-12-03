"""
RagChroma

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-02 14:36:25.970592

Decorate a query prompt with RAG results returned from a chromadb database.
"""

import typing

import chromadb

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class RagChroma(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        host: str,
        port: int,
        tenant: str,
        database: str,
        collection: str,
        target: str,
        results: int,
        **kwargs,
    ):
        """
        Parameters
        ----------
        host : str
            The address of the chromadb database.
        port : int
            The port of the chromadb database.
        tenant : str
            The tenant to use for the query.
        database : str
            The database name where the collection is stored.
        collection : str
            The collection to query for context documents.
        target : str
            Target key in received message.
        results : int
            Number of documents to include into results.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._host = host
        self._port = port
        self._tenant = tenant
        self._database = database
        self._collection = collection
        self._target = target

        self._client = None
        self._results = results

    def warmup(self):
        """Warmup the node"""
        self._client = chromadb.HttpClient(
            host=self._host,
            port=self._port,
            ssl=False,
            tenant=self._tenant,
            database=self._database,
        )

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        if prop == 'results':
            self._results = value

    def start(self):
        """Start the node"""
        self._collection = self._client.get_collection(name=self._collection)

        super().start()

    def update(self, message: Message[ObjectPayload]):
        """Receive data from upstream, transmit data downstream"""
        query = message.payload[self._target]

        results = self._collection.query(
            query_texts=[query], n_results=self._results
        )

        documents = results['documents'][0]

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            timers_from=message,
            payload=Draft(ObjectPayload),
        )

        to_send.payload['documents'] = documents

        self.transmit(to_send)
