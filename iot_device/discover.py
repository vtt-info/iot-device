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
        # __devices: uid --> device
        self.__devices = {}
        self.__devices_lock = threading.Lock()

    def add_device(self, device):
        """Add device to dict; set age to zero if it is already in the dict."""   
        dev = self.__devices.get(device.uid)
        if dev:
            # device already registerd, mark as seen
            dev.seen()
        # new device
        with self.__devices_lock:
            self.__devices[device.uid] = device

    def get_device(self, uid):
        with self.__devices_lock:
            return self.__devices.get(uid)

    def __enter__(self):
        self.__devices_lock.acquire()
        print(f"Discover.__enter__ __devices={self.__devices} values={self.__devices.values()} {type(self.__devices.values())}")
        return self.__devices.values()

    def __exit__(self, type, value, traceback):
        self.__devices_lock.release()
