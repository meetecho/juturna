from juturna.components import Message
from juturna.components import BaseNode

import redis


class NotifierRedis():
    def __init__(self, endpoint: str):
        super().__init__('sink')

        self._endpoint = endpoint


    def update(self, message: Message):
        ...
