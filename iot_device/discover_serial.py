from .discover import Discover
from .serial_connection import SerialConnection

import time
import logging
import serial
import serial.tools.list_ports

logger = logging.getLogger(__file__)

# Vendor IDs
ADAFRUIT_VID = 0x239A  # Adafruit board
PARTICLE_VID = 0x2B04  # Particle
ESP32_VID    = 0x10C4  # ESP32 via CP2104
STM32_VID    = 0xf055  # STM32 usb port

COMPATIBLE_VID = { ADAFRUIT_VID, PARTICLE_VID, STM32_VID, ESP32_VID }


class DiscoverSerial(Discover):

    def __init__(self):
        super().__init__()

    def scan(self):
        # scan & replicate serial ports
        try:
            for port in serial.tools.list_ports.comports():
                if port.vid in COMPATIBLE_VID:
                    # print(f"discovered {port.device}")
                    con = SerialConnection(port.device, f"{port.product} by {port.manufacturer}")
                    self.add_device(con)
                elif port.vid:
                    print("found {} with unknown VID {:02X} (ignored)".format(port, port.vid))
        except Exception as e:
            logger.exception(f"Error in scan: {e}")


#####################################################################

class Output:
    def ans(self, value):
        print(value.decode(), flush=True, end="")

    def err(self, value):
        print(value.decode(), flush=True, end="")

code = [

b"print(2**10)",

"""
for i in range(3):
    print(i, i**2, i**3)
""",

"uid",

"print('4/sf)",

"""
def a():
    print('A')
    # raise ValueError("a(): no value!")
    print('returning from a()')

def b():
    print('B')
    a()
    print('returning from b()')

def c():
    print('C')
    b()
    print('returning from c()')

c()
# print("after exception")
""",
"a = 5",
"print(a)",
"softreset",
"print(a)"

]

def main():
    ds = DiscoverSerial()
    while True:
        ds.scan()
        with ds as devices:
            for d in devices.values():
                if d.age > 1:
                    print(f"skipping old device {d}")
                    continue
                print(f"before sync: get_time = {d.get_time()}")
                d.sync_time()
                print(f"after  sync: get_time = {d.get_time()}")

                for c in code:
                    print('-'*50)
                    try:
                        if c == "softreset":
                            print("SOFTRESET")
                            d.softreset()
                        elif c == "uid":
                            print(f"UID {d.uid}")
                        else:
                            print(f"EVAL {c}")
                            d.eval(c, Output())
                    except ReplException as re:
                        print(f"***** ERROR {re}")    
            print()           
        time.sleep(3)

if __name__ == "__main__":
    main()
