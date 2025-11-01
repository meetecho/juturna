from ultralytics import YOLO

from juturna.components import Message
from juturna.components import Node

from juturna.payloads._payloads import ImagePayload


class TrackerYolo(Node[ImagePayload, ImagePayload]):
    def __init__(
        self,
        model: str,
        device: str,
        targets: list,
        confidence: float,
        half: bool,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.logger.info(f'received extras: {kwargs}')

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

        self.logger.info('tracker ready')

    def update(self, message: Message[ImagePayload]):
        assert self._model != None

        image = message.payload.image
        results = self._model.predict(
            image,
            verbose=False,
            classes=self._classes,
            conf=self._confidence,
            half=self._half,
        )

        annotated = results[0].plot()

        to_send = Message[ImagePayload](
            creator=self.name,
            version=message.version,
            payload=ImagePayload(
                image=annotated,
                width=annotated.shape[1],
                height=annotated.shape[0],
                depth=annotated.shape[2],
                pixel_format=message.payload.pixel_format,
                timestamp=message.payload.timestamp,
            ),
            timers_from=message,
        )

        to_send.meta['annotations'] = results[0]

        self.transmit(to_send)
