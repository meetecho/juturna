import typing

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BasePayload


class LoggerProperty(Node[BasePayload, BasePayload]):
    def __init__(self,
                 target: str,
                 value: typing.Any,
                 match_any: bool,
                 in_meta: bool,
                 **kwargs):
        super().__init__(**kwargs)

        self._target = target
        self._value = value
        self._match_any = match_any
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

            if self._match_any or (_t[self._target] == self._value):
                self.logger.info(
                    f'{self.name} match: {self._target} == {_t[self._target]}')
        except Exception as e:
            ...