from .connection import Connection

import time
from serial import Serial, SerialException

class SerialConnection(Connection):

    def __init__(self, port, description, baudrate=115200):
        super().__init__()
        self.__port = port
        self.__description = description
        self.__baudrate = baudrate
        self.__connect()

    def __connect(self):
        self.__serial = Serial(self.__port, self.__baudrate, parity='N')

    def read(self, size=1):
        for _ in range(2):
            try:
                return self.__serial.read(size)
            except SerialException:
                self.__connect()
        raise SerialException("read failed")

    def read_all(self):
        for _ in range(2):
            try:
                return self.__serial.read_all()
            except SerialException:
                self.__connect()
        raise SerialException("read_all failed")

    def write(self, data):
        for _ in range(2):
            try:
                n = 0
                for i in range(0, len(data), 256):
                    n += self.__serial.write(data[i:min(i+256, len(data))])
                    time.sleep(0.01)
                return n
            except SerialException:
                self.__connect()
        raise SerialException("write failed")


    def close(self):
        self._serial.close()

    def __eq__(self, other):
        return isinstance(other, SerialConnection) and self.__port == other.__port

    def __hash__(self):
        return hash(self.__port)