from .rsync import Rsync

from abc import ABC, abstractmethod
import threading
import time
import logging

logger = logging.getLogger(__file__)


class Device(ABC):

    def __init__(self):
        self.__lock = threading.Lock()
        with self as repl:
            self.__uid = repl.uid

    @property
    def uid(self):
        return self.__uid

    @abstractmethod
    def read(self, size=1) -> bytes:
        """Read size bytes"""
        return b''

    @abstractmethod
    def read_all(self) -> bytes:
        """Read all available data"""
        return b''

    @abstractmethod
    def write(self, data: bytes):
        """Writes data"""
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def __hash__(self):
        return self.__uid

    def read_until(self, pattern: bytes, timeout=5):
        """Read until pattern
        Raises TimeoutError
        """
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                raise TimeoutError(f"Timeout reading from IoT device, got '{result}', expect '{pattern}'")
            result.extend(self.read(size=1))
        return result

    @property
    def age(self) -> float:
        """Time in seconds since seen was last called.
        Used to "prune" devices gone offline.
        """
        try:
            self.__seen
        except AttributeError:
            self.__seen = 0
        return time.monotonic() - self.__seen 

    def seen(self):
        """Set age to zero."""
        self.__seen = time.monotonic()

    def __eq__(self, other):
        return self == other

    def __enter__(self) -> Rsync:
        self.__lock.acquire()
        return Rsync(self)

    def __exit__(self, type, value, traceback):
        self.__lock.release()
