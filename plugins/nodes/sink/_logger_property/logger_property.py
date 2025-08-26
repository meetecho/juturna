import typing
import logging

from juturna.components import BaseNode
from juturna.components import Message

from juturna.payloads._payloads import BasePayload


class LoggerProperty(BaseNode[BasePayload, BasePayload]):
    def __init__(self, target: str, value: typing.Any, in_meta: bool):
        super().__init__('sink')

        self._target = target
        self._value = value
        self._in_meta = in_meta

    def configure(self):
        ...

    def warmup(self):
        ...

    def set_on_config(self, property: str, value: typing.Any):
        ...

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    def destroy(self):
        ...

    def update(self, message: Message[BasePayload]):
        try:
            _t = message.meta if self._in_meta else message.payload

            if _t[self._target] == self._value:
                logging.info(f'{self.name} match: {self._target} = {self._value}')
        except Exception as e:
            ...