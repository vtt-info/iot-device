from .rsync import Rsync

from abc import ABC, abstractmethod
import threading
import logging

logger = logging.getLogger(__file__)

"""
Thread-safe dict uid-->device.
Iterate over all known devices (regardless of age):

    ds = DiscoverSerial()
    with ds as devices:
        for d in devices:
            print(d)
"""

class Discover(ABC):

    def __init__(self):
        # maintain two dicts (add only, so consistency is no issue):
        #   __devices: uid --> device
        #   __connections: connection_hash --> device
        self.__devices = {}
        self.__devices_lock = threading.Lock()
        self.__connections = {}

    def add_device(self, connection):
        """Add device to dict; set age to zero if it is already in the dict."""   
        dev = self.__connections.get(connection.__hash__())
        if dev:
            # device already registerd, mark as seen
            dev.seen()
        # new device
        dev = Rsync(connection)
        with self.__devices_lock:
            self.__devices[dev.uid] = dev

    def get_device(self, uid):
        with self.__devices_lock:
            return self.__devices.get(uid)

    def __enter__(self):
        self.__devices_lock.acquire()
        return self.__devices.values()

    def __exit__(self, type, value, traceback):
        self.__devices_lock.release()
