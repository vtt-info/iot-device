from contextlib import contextmanager
from serial import SerialException
import inspect
import time
import logging

logger = logging.getLogger(__file__)


"""
Example:

    # constructor: specify hostname or uid
    mcu = MCU('hostname': 'my_awesome_microcontroller')
    with device.eval("print(2**40); input()", output) as stdin:
        # connects to mcu,
        # evaluates code,
        # sends data to stdin,
        # reports results (stdout, stdin) on output
        stdin.write("blah ...")
"""

MCU_RAW_REPL      = b'\x01'    # enter raw repl
MCU_ABORT         = b'\x03'    # abort
MCU_RESET         = b'\x04'    # reset
MCU_EVAL          = b'\r\x04'  # start evaluation (raw repl)
EOT               = b'\x04'

# esp32 cannot handle more than 255 bytes per transfer
# not sure why ...
# what's the performance penalty on nrf52?
BUFFER_SIZE = 254 # 2048

class ReplException(Exception):
    pass


class Repl:

    def __init__(self, device):
        self.__device = device

    @property
    def uid(self):
        return self.eval_func(_uid)

    @property
    def device(self):
        return self.__device

    def eval(self, code, output):
        """Eval code on remote (Micro)Python VM.
           Results are returned via the response call-back handler (class),
           with methods
              def ans(value)
              def err(value)
        """
        try:
            self.__exec_part_1(code)
            self.__exec_part_2(output)
            # successful evaluation implies device is online
            self.device.seen()   
        except ReplException:
            raise
        except Exception as e:
            logger.debug(f"Exception in eval {code}")
            raise ReplException(e)

    def eval_func(self, func, *args, xfer_func=None, output=None, **kwargs):
        """Call func(*args, **kwargs) on (Micro)Python board."""
        try:
            args_arr = [repr(i) for i in args]
            kwargs_arr = ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
            func_str = inspect.getsource(func).replace('BUFFER_SIZE', str(BUFFER_SIZE))
            func_str += 'import os\n'
            func_str += 'os.chdir("/")\n'
            func_str += 'output = ' + func.__name__ + '('
            func_str += ', '.join(args_arr + kwargs_arr)
            func_str += ')\n'
            func_str += 'if output != None: print(output)\n'
            # logger.debug(f"eval_func: {func_str}")
            start_time = time.monotonic()
            self.__exec_part_1(func_str)
            if xfer_func:
                xfer_func(self, *args, **kwargs)
                logger.debug(f"returned from xfer_func")
            output = self.__exec_part_2(output)
            logger.debug("eval_func: {}({}) --> {},   in {:.3} s)".format(
                func.__name__,
                repr(args)[1:-1],
                output,
                time.monotonic()-start_time))
            if output:
                try:
                    output = output.decode().strip()
                except UnicodeDecodeError:
                    pass
            # successful evaluation implies device is online
            self.device.seen()   
            return output
        except SyntaxError as se:
            logger.error(f"Syntax {se}")

    def softreset(self):
        """Reset MicroPython VM"""
        try:
            self.device.write(MCU_ABORT)
            self.device.write(MCU_RESET)
            self.device.write(b'\n')
            self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')
            # successful evaluation implies device is online
            self.device.seen()   
            logger.debug("VM reset")
        except Exception as e:
            logger.debug("Exception in softreset")
            raise ReplException(e)

    def get_time(self):
        # get struct time from mcu
        st = eval(self.eval_func(_get_time))
        if len(st) < 9:
            st += (-1, )
        return st

    def sync_time(self, tolerance=10):
        self.eval_func(_set_time, tuple(time.localtime()), tolerance)

    def device_characteristics(self):
        return eval(self.eval_func(_device_characteristics))

    def __exec_part_1(self, code):
        if isinstance(code, str):
            code = code.encode()
        # logger.debug(f"EVAL {code.decode()}")
        self.device.write(MCU_ABORT)
        self.device.write(MCU_ABORT)
        self.device.write(MCU_RAW_REPL)
        self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')
        self.device.write(code)
        self.device.write(MCU_EVAL)
        # process result of format "OK _answer_ EOT _error_message_ EOT>"
        if self.device.read(2) != b'OK':
            raise ReplException(f"Cannot eval '{code}'")

    def __exec_part_2(self, output):
        if output:
            logger.debug(f"_exec_part_2 ...")
            while True:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.ans(ans[0])
                if len(ans) > 1:      # 1st EOT
                    if len(ans[1]): output.err(ans[1])
                    if len(ans) > 2:  # 2nd EOT
                        return
                    break             # look for 2nd EOT below
            # read error message, if any
            while True:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.err(ans[0])
                if len(ans) > 1:      # 2nd EOT
                    break
        else:
            result = bytearray()
            while True:
                result.extend(self.device.read_all())
                if result.count(EOT) > 1:
                    break
            s = result.split(EOT)
            logger.debug(f"repl_ops s={s}")
            if len(s[1]) > 0:
                logger.debug(f"_exec_part_2 s={s} s[1]={s[1]}")
                raise ReplException(s[1].decode())
            return s[0]

##########################################################################
# Code running on MCU

def _uid():
    try:
        import machine   # pylint: disable=import-error
        _id = machine.unique_id()
    except:
        try:
            import microcontroller   # pylint: disable=import-error
            _id = microcontroller.cpu.uid
        except:
            return None
    return ":".join("{:02x}".format(x) for x in _id)

def _get_time():
    import time
    return tuple(time.localtime())

# set mcu time to timestamp if they differ by more than tolerance seconds
def _set_time(st, tolerance=5):
    import time
    host  = time.mktime(st)
    local = time.time()
    if abs(host-local) < tolerance:
        return
    try:
        # CircuitPython
        import rtc
        rtc.RTC().datetime = st
    except ImportError:
        # MicroPython
        import machine
        # convert to Micropython's non-standard ordering ...
        st = list(st)
        st.insert(3, st[6])
        st[7] = 0
        machine.RTC().datetime(st[:8])

# device_characteristics
def _device_characteristics():
    import sys, time
    try:
        sys.stdout.buffer
        sys.stdin.buffer
        has_buffer = True
    except AttributeError:
        has_buffer = False

    try:
        import binascii
        has_binascii = True
        binascii
    except ImportError:
        has_binascii = False

    #     year  m  d  H  M  S   W  dy
    st = (2000, 1, 1, 0, 0, 0, -1, -1, -1)
    epoch = 946684800-time.mktime(st)

    return { 'has_buffer': has_buffer, 'has_binascii': has_binascii, 'time_offset': epoch }

##########################################################################
# Example

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
    from .discover_serial import DiscoverSerial
    ds = DiscoverSerial()
    while True:
        ds.scan()
        with ds as devices:
            for d in devices:
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