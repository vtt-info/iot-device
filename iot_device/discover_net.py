from .discover import Discover
from .net_device import NetDevice
from .config_store import Config

import socket
import json
import time
import logging

logger = logging.getLogger(__file__)

class DiscoverNet(Discover):

    def __init__(self):
        # find & serve devices advertised online
        super().__init__()

    def scan(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Note: port 255.255.255.255 fails with OSError: 
            #     [Errno 49] Can't assign requested address
            # ??? get OSError 98 when server is not running???
            port = Config.get('advertise_port')
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(6)
            try:
                s.bind(('0.0.0.0', port))
            except:
                logger.error("Cannot bind to port {}".format(port))
                raise
            start = time.monotonic()
            while (time.monotonic() - start) < 4:
                try:
                    msg = json.loads(s.recv(1024).decode())
                    if msg['protocol'] != 'repl':
                        logger.error(f"Found device with unknown protocol {msg['protocol'] (msg)}")
                        continue
                    logger.debug(f"Discovered {msg}")
                    if not self.has_key(msg['uid']):
                        self.add_device(NetDevice(msg))
                except socket.timeout:
                    logger.debug("Timeout in discovery")
                except json.JSONDecodeError:
                    logger.debug(f"Received malformed advertisement: {msg}")
    

##########################################################################
# Main

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

"""import time
time.sleep(2)""",

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
    from .repl import ReplException
    from serial import SerialException
    import sys
    import threading

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    discover = DiscoverNet()

    def scanner():
        while True:
            discover.scan()
            time.sleep(3)

    threading.Thread(target=scanner, daemon=True).start()



    while (True):
        # discover.scan()
        with discover as devices:
            for dev in devices:
                try:
                    print('-'*40, dev)
                    if dev.age > 10:
                        print(f"skipping old device {dev.uid} age = {dev.age:.1f}s")
                        continue
                    print("wait dev as repl:")
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
        time.sleep(5)

if __name__ == "__main__":
    main()