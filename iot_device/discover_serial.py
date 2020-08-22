from .discover import Discover
from .repl import ReplException
from .serial_device import SerialDevice

from serial import SerialException
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
                    logger.debug(f"found {port.device}")
                    if not self.has_key(port.device):
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

def listfiles():
    # this function runs on the MCU ...
    from os import listdir
    return listdir()

def main():
    ds = DiscoverSerial()
    while True:
        print("scan for devices ...")
        ds.scan()
        with ds as devices:
            for dev in devices:
                try:
                    print('\n', '-'*40, dev)
                    if dev.age > 1:
                        print(f"skipping old device")
                        continue
                    with dev as repl:
                        # sync time ...
                        print(f"before sync: get_time = {repl.get_time()}")
                        repl.sync_time()
                        print(f"after  sync: get_time = {repl.get_time()}")

                        # eval ...
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

                        # eval_func ...
                        print(f"listfiles: {repl.eval_func(listfiles)}")
                        fn = 'lib/adafruit_requests.py'
                        print(f"cat({fn}):")
                        repl.cat(Output(), fn)
                        print('\n', '-'*10)
                        repl.fget('lib/adafruit_requests.py', 'tmp/adafruit_requests.py')
                        print('\n', '-'*10)
                        fn = 'delete_me.txt'
                        repl.fput(f'tmp/{fn}', fn)
                        print('\n', '-'*10)
                        print(f"cat({fn})")
                        repl.cat(Output(), fn)
                        print(f"new file {fn} on mcu ...")
                        print(f"listfiles: {repl.eval_func(listfiles)}")
                        print("after rm ...")
                        repl.rm_rf(fn)
                        print(f"listfiles: {repl.eval_func(listfiles)}")

                        # rsync
                        print('-'*10, 'rlist')
                        repl.rlist(Output())
                        print('-'*10, 'rdiff')
                        repl.rdiff(Output())
                        print('-'*10, 'rsync')
                        repl.rsync(Output())
                except SerialException as se:
                    print(f"SerialException in DiscoverSerial.main: {se}")
                except OSError as oe:
                    print(f"OSError in DiscoverSerial.main: {oe}")
            print()           
        time.sleep(2)

if __name__ == "__main__":
    main()
