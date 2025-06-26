from typing import TypeVar

from juturna.payloads._payloads import AudioPayload
from juturna.payloads._payloads import ImagePayload
from juturna.payloads._payloads import VideoPayload
from juturna.payloads._payloads import BytesPayload
from juturna.payloads._payloads import ObjectPayload


T_Input = TypeVar('T_Input', AudioPayload, ImagePayload, VideoPayload,
                  BytesPayload, ObjectPayload, None)
T_Output = TypeVar('T_Output', AudioPayload, ImagePayload, VideoPayload,
                   BytesPayload, ObjectPayload, None)