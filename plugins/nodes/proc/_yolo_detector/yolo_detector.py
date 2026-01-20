"""
DetectorYolo

@ Author: Paolo Saviano, Antonio Bevilacqua
@ Email: psaviano@meetecho.com, abevilacqua@meetecho.com

Prepare image and annotate detections using a custom YOLO model.
It can plot the annotations on the image or just pass them as metadata.
For more info about the models, see here: https://github.com/ultralytics/ultralytics
"""

from ultralytics import YOLO
import numpy as np

from juturna.components import Message
from juturna.components import Node

from juturna.payloads._payloads import ImagePayload


class YoloDetector(Node[ImagePayload, ImagePayload]):
    """Node implementation class"""

    def __init__(
        self,
        model: str,
        device: str,
        targets: list,
        confidence: float,
        half: bool,
        plot: bool,
        warmup: list,
        **kwargs,
    ):
        """
        Parameters
        ----------
        model : str
            Name of the model to use
        device : str
            Where to run inference (cpu or cuda).
        targets : list
            List of class to target during inference.
        confidence : float
            Minimum confidence to mark a positive.
        half : bool
            Enable half precision to speed up inference time.
        plot : bool
            Whether to plot annotations on the image or not.
        warmup : list
            List of image sizes to use for warmup inferences.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._model_name = model
        self._device = device
        self._targets = targets
        self._confidence = confidence
        self._half = half
        self._plot = plot
        self._warmup = warmup
        self._model = None
        self._classes = None

    def warmup(self):
        """Load model and run dummy inferences to speed up later processing"""
        self._model = YOLO(self._model_name)
        self._model.to(self._device)
        self._classes = (
            [
                {v: k for k, v in self._model.names.items()}[t]
                for t in self._targets
            ]
            if len(self._targets) > 0
            else None
        )

        for size in self._warmup:
            dummy_img = np.zeros((size, size, 3), dtype=np.uint8)
            _ = self._model.predict(dummy_img, verbose=False, imgsz=size)

        self.logger.info('tracker ready')

    def update(self, message: Message[ImagePayload]):
        """Process an incoming message"""
        assert self._model is not None

        image = message.payload.image
        image_format = message.payload.pixel_format
        meta = dict(message.meta)

        normalized_image = None
        results = None

        to_send = Message[ImagePayload](
            creator=self.name,
            version=message.version,
            payload=(),
            timers_from=message,
        )

        with to_send.timeit(self.name + '_image_preprocessing_numpy'):
            if image.shape[2] == 4 and image_format == 'RGB':
                normalized_image = image[
                    :, :, 2::-1
                ]  # remove alpha and convert RGB→BGR
            elif image.shape[2] == 4:
                normalized_image = image[:, :, :3]  # remove alpha only
            elif image_format == 'RGB':
                normalized_image = image[:, :, ::-1]  # only RGB→BGR
            else:
                normalized_image = image  # no modification

        with to_send.timeit(self.name + '_inference'):
            results = self._model.predict(
                normalized_image,
                verbose=False,
                classes=self._classes,
                conf=self._confidence,
                half=self._half,
                imgsz=max(image.shape[0], image.shape[1]),
            )

        annotated = None
        pixel_format = None

        with to_send.timeit(self.name + '_postprocessing'):
            annotated = results[0].plot() if self._plot else image
            pixel_format = 'BGR' if self._plot else image_format

        to_send.payload = ImagePayload(
            image=annotated,
            width=annotated.shape[1],
            height=annotated.shape[0],
            depth=annotated.shape[2],
            pixel_format=pixel_format,
            timestamp=message.payload.timestamp,
        )

        if 'annotations' not in meta:
            meta['annotations'] = {}

        if len(results[0].boxes) > 0:
            meta['annotations'][self.name] = results[0].boxes

        to_send.meta = meta

        self.transmit(to_send)
