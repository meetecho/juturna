from ultralytics import YOLO

from juturna.components import Message
from juturna.components import BaseNode


class TrackerYolo(BaseNode):
    def __init__(self,
                 model: str,
                 device: str,
                 targets: list,
                 confidence: float,
                 half: bool):
        super().__init__('proc')

        self._model_name = model
        self._device = device
        self._targets = targets
        self._confidence = confidence
        self._half = half

        self._model = None
        self._classes = None

    def warmup(self):
        self._model = YOLO(self._model_name)
        self._model.to(self._device)
        self._classes = [
            {v: k for k, v in self._model.names.items()}[t]
            for t in self._targets
        ]

    def update(self, message: Message):
        frame = message.payload
        results = self._model.predict(frame,
                                      verbose=False,
                                      classes=self._classes,
                                      conf=self._confidence,
                                      half=self._half)

        to_send = Message(creator=self.name, version=message.version)
        to_send.payload = frame
        to_send.meta['annotations'] = results[0]

        self.transmit(to_send)
