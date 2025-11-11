from juturna.components import Message
from juturna.components import Node

from juturna.payloads._payloads import ObjectPayload

import redis


class NotifierRedis(Node[ObjectPayload, None]):
    def __init__(self, endpoint: str):
        super().__init__('sink')

        self._endpoint = endpoint


    def update(self, message: Message[ObjectPayload]):
        ...
