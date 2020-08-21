from .discover import Discover
from .repl import ReplException
from .serial_device import SerialDevice

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
                    dev = SerialDevice(port.device, f"{port.product} by {port.manufacturer}")
                    self.add_device(dev)
                elif port.vid:
                    logger.info("found {} with unknown VID {:02X} (ignored)".format(port, port.vid))
        except Exception as e:
            logger.exception(f"Error in scan: {e}")


#####################################################################

class Output:
    def ans(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

    def err(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

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
            print(f"devices {devices} {type(devices)}")
            for dev in devices:
                print('\n', '-'*40, dev)
                if dev.age > 1:
                    print(f"skipping old device")
                    continue
                with dev as repl:
                    print(f"before sync: get_time = {repl.get_time()}")
                    repl.sync_time()
                    print(f"after  sync: get_time = {repl.get_time()}")

                    for c in code:
                        print('-'*50)
                        try:
                            if c == "softreset":
                                print("SOFTRESET")
                                repl.softreset()
                            elif c == "uid":
                                print(f"UID {repl.uid}")
                            else:
                                print(f"EVAL {c}")
                                repl.eval(c, Output())
                        except ReplException as re:
                            print(f"***** ERROR {re}")
                    print('-'*10, 'rlist')
                    repl.rlist(Output())
                    print('-'*10, 'rdiff')
                    repl.rdiff(Output())
                    print('-'*10, 'rsync')
                    repl.rsync(Output())
            print()           
        time.sleep(10)

if __name__ == "__main__":
    main()
