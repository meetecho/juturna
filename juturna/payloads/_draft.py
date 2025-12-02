"""
As payload dataclasses are frozen, progressively creating a payload object can
be tricky. This module offers a way of drafting payloads, storing all its keys
and values so that they can be edited without restriction, and eventually
compiled into a concrete payload.
"""

from typing import Any

from dataclasses import fields


class Draft[T]:
    """
    Payloads can be built using drafts. A draft stores the payload values, and
    once it is compiled an actual payload will be generated.
    """

    def __init__(self, payload_type: T, copy_from: T | None = None):
        """
        Parameters
        ----------
        payload_type : T
            The type of payload that should be drafted. Allowed fields will be
            selected from this.
        copy_from : T
            A payload that can be used to fill initial values for the draft.

        """
        object.__setattr__(self, '_payload_type', payload_type)
        object.__setattr__(self, '_draft', dict())

        valid_fields = (
            None
            if issubclass(payload_type, dict)
            else {f.name for f in fields(payload_type)}
        )

        object.__setattr__(self, '_valid_fields', valid_fields)

        if copy_from is None:
            return

        if not isinstance(copy_from, payload_type):
            raise TypeError(
                f'cannot copy from {type(copy_from)} into draft {payload_type}'
            )

        if self._valid_fields is None:
            self._draft.update(copy_from)

            return

        for field_name in self._valid_fields:
            self._draft[field_name] = getattr(copy_from, field_name)

    def __setattr__(self, key: str, value: Any):
        if self._valid_fields is not None and key not in self._valid_fields:
            raise AttributeError(
                f'{key} not allowed in {self._payload_type.__name__}'
            )

        self._draft[key] = value

    def __setitem__(self, key: str, value: Any):
        if self._valid_fields is not None and key not in self._valid_fields:
            raise AttributeError(
                f'{key} not allowed in {self._payload_type.__name__}'
            )

        self._draft[key] = value

    def __getattr__(self, key: str) -> Any:
        return self._draft[key]

    def clear(self):
        """Clear all stored keys and values"""
        self._draft = dict()

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
            raise TypeError('payload draft does not have destination type')

        return self._payload_type(**self._draft)
