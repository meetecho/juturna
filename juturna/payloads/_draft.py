"""
As payload dataclasses are frozen, progressively creating a payload object can
be tricky. This module offers a way of drafting payloads, storing all its keys
and values so that they can be edited without restriction, and eventually
compiled into a concrete payload.
"""

from typing import Any


class PayloadDraft[T]:
    """
    Payloads can be built using drafts. A draft stores the payload values, and
    once it is compiled an actual payload will be generated.
    """

    def __init__(self):
        self._payload_type: T | None = None
        self._draft = dict()

    def open(self, payload_type: type):
        """
        Open the draft by assigning the type of payload it will compile into.

        Parameters
        ----------
        payload_type : type
            The type of payload the draft can generate.

        """
        if self._payload_type is None:
            self._payload_type = payload_type

    def clear(self):
        """Clear all stored keys and values"""
        self._draft = dict()

    def is_open(self) -> bool:
        """
        Check if the draft is open.

        Returns
        -------
        bool
            True if the draft is open (payload type is set), False otherwise.

        """
        return self._payload_type is not None

    def add(self, key: str, value: Any):
        """
        Add new item to the draft.

        Parameters
        ----------
        key : str
            The key of the new item. It will be used as argument name when the
            payload is compiled.
        value : Any
            The value of the new item.

        """
        self._draft[key] = value

    def compile(self) -> T:
        """
        Compile the payload, using all the stored key-value items.

        Returns
        -------
        BasePayload
            A new payload.

        Raises
        ------
        TypeError
            If the draft was not open, so the payload type was not set, the
            method raises a TypeError.

        """
        if not self._payload_type:
            raise TypeError('payload draft not open')

        return self._payload_type(**self._draft)
