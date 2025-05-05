import copy
import threading
import logging

from juturna.components import Message


class Buffer:
    """Data storage class

    A buffer stores the provided data, and makes it available to nodes that
    polls it for updates.

    """
    def __init__(self, name: str = ''):
        self._received = 0
        self._this_message = None
        self._name = name
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    def update(self, message: Message | None):
        """
        Update the datum stored in the buffer with a new provided datum. If the
        passed message is None, then nothing will be updated. The method locks
        the buffer to prevent readers from querying the wrong data version
        while the datum is being updated.

        Parameters
        ----------
        message : Message | None
            The message with the new datum in its payload.
        """
        if message is None:
            logging.warning(f'invalid message received in {self._name}')

            return

        with self._lock:
            self._this_message = copy.deepcopy(message)
            self._received += 1

    def version(self) -> int | None:
        """
        Return the version of the datum currently stored. If the buffer is
        empty, the method returns None.

        Returns
        -------
        int | None
            The version of the data currently stored, None if the buffer is
            empty.

        .. deprecated::
        """
        if self._this_message:
            return self._this_message.version

        return None

    def count(self) -> int:
        """
        Return the number of messages received by the buffer. This number may
        differ from the version of the current datum if any messages were lost
        from the source.

        Returns
        -------
        int
            The number of packages received from the buffer.
        """
        return self._received

    def data(self) -> Message:
        """
        Return a copy of the datum currently stored in the buffer.

        Returns
        -------
        Message
            A copy of the message currently stored in the buffer.
        """
        return copy.deepcopy(self._this_message)

    def get_updated(self, last_version: int) -> Message | None:
        """
        Fetch the message stored in the buffer. This method locks the buffer
        and atomically queries the message version against a provided version.
        If the buffer contains an updated version of the message, then a copy
        is returned, otherwise it returns None.

        Parameters
        ----------
        last_version : int
            The version to check the buffer content against.

        Returns
        -------
        Message | None
            A copy of the stored message, or None if the passed version is less
            than the buffer version.
        """
        with self._lock:
            if last_version >= self.version():
                return None

            return copy.deepcopy(self._this_message)
