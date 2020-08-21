from abc import ABC, abstractmethod
import time
import logging


logger = logging.getLogger(__file__)


class ConnectionException(Exception):
    pass


class Connection(ABC):

    def __init__(self):
        self._uid = None
        super().__init__()

    @abstractmethod
    def read(self, size=1):
        """Read size bytes
        Returns bytes read
        Raises ConnectionException
        """
        return b''

    @abstractmethod
    def read_all(self):
        """Read all available data
        Raises ConnectionException
        """
        return b''

    @abstractmethod
    def write(self, data):
        """Writes data (bytes)
        Raises ConnectionException
        """
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def __hash__(self):
        pass

    def read_until(self, pattern, timeout=5):
        """Read until pattern
        Raises ConnectionException, TimeoutError
        """
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                raise TimeoutError(f"Timeout reading from IoT device, got '{result}', expect '{pattern}'")
            result.extend(self.read(size=1))
        return result

    def __eq__(self, other):
        return self == other

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.uid})"
