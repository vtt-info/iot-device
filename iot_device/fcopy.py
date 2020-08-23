from .repl import Repl, BUFFER_SIZE
from .config_store import Config

import binascii
import os
import logging

logger = logging.getLogger(__file__)


"""
Device with added features:
* fget, fput - copy files between host and remote device
* file_size
"""


class Fcopy(Repl):

    def __init__(self, connection):
        super().__init__(connection)

    def file_size(self, path):
        return int(self.eval_func(_file_size, path))

    def makedirs(self, path):
        return self.eval_func(_makedirs, path)

    def rm_rf(self, path, recursive=False):
        return self.eval_func(_rm_rf, path, recursive)

    def cat(self, output, filename):
        self.eval_func(_cat, filename, output=output)

    def fget(self, remote_file, local_file):
        filesize = self.file_size(remote_file)
        print(f"fget: filesize {remote_file} = {filesize}")
        if filesize < 0:
            return False
        return self.eval_func(_mcu_read, remote_file, local_file, filesize, xfer_func=_host_write)

    def fput(self, local_file, remote_file):
        # upload file to MCU
        if os.path.isdir(local_file):
            # Copy files only, not directories
            return False
        with open(local_file, 'rb') as f:
            # Check if it's a binary file that could upset REPL (ctrl-C, ...)
            include = [ord(x) for x in '\a\b\f\n\t\v']
            exclude = bytes([ x for x in range(32) if not x in include ])
            binary = any([x in exclude for x in f.read()])
        filesize = os.path.getsize(local_file)
        self.makedirs(os.path.dirname(remote_file))
        res = self.eval_func(_mcu_write, local_file, remote_file, filesize, binary, xfer_func=_host_read)
        return res


##########################################################################
# Code running on MCU

def _mcu_write(local_file, remote_file, filesize, binary):
    # receives file from host and writes to flash as `filename`
    import sys
    try:
        if binary:
            import binascii
        with open(remote_file, 'wb') as dst_file:
            bytes_remaining = filesize
            if binary: bytes_remaining *= 2    # hexlify doubles size
            write_buf = bytearray(BUFFER_SIZE)
            read_buf  = bytearray(BUFFER_SIZE)
            while bytes_remaining > 0:
                read_size = min(bytes_remaining, BUFFER_SIZE)
                buf_remaining = read_size
                buf_index = 0
                while buf_remaining > 0:
                    bytes_read = sys.stdin.readinto(read_buf, bytes_remaining)  # pylint: disable=no-member
                    if bytes_read > 0:
                        write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                        buf_index += bytes_read
                        buf_remaining -= bytes_read
                dst_file.write(binascii.unhexlify(write_buf[0:read_size]) if binary else write_buf[0:read_size])
                # Send back an ack as a form of flow control
                sys.stdout.write(b'\x06')
                bytes_remaining -= read_size
    except:
        # signal error (anything but b'\x06')
        sys.stdout.write(b'\x07')
        raise

def _host_read(device, local_file, remote_file, filesize, binary):
    # reads file from host and sends to MCU
    # pass to `ReplOps.eval_func` as the xfer_func argument
    # matches up with mcu_write
    host_dir = os.path.expanduser(Config.get('host_dir'))
    src_file_name = os.path.join(host_dir, local_file)
    buf_size = BUFFER_SIZE // 2 if binary else BUFFER_SIZE
    with open(src_file_name, 'rb') as src_file:
        bytes_remaining = filesize
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, buf_size)
            buf = src_file.read(read_size)
            if binary:
                buf = binascii.hexlify(buf)
            device.write(buf)
            # Wait for ack so we don't get too far ahead of the remote
            ack = device.read(1)
            if ack != b'\x06':
                logger.error(f"got {ack}, expected b'\\x06'")
                return False
            bytes_remaining -= read_size
    return True
    
def _mcu_read(remote_file, local_file, filesize):
    # reads file from flash and sends to host
    import sys
    with open(remote_file, 'rb') as src_file:
        bytes_remaining = filesize
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, BUFFER_SIZE)
            buf = src_file.read(read_size)
            # buffer is necessary!
            # But not available on samd51
            sys.stdout.buffer.write(buf)
            bytes_remaining -= read_size
            # Wait for an ack so we don't get ahead of the remote
            ack = sys.stdin.read(1)
            if ack != '\x06':
                raise ValueError("Expected '\\x06', got '{}'".format(ord(ack)))

def _host_write(device, remote_file, local_file, filesize):
    # receives file from MCU and saves on host
    # pass to `ReplOps.eval_func` as the xfer_func argument
    # matches up with mcu_read
    host_dir = os.path.expanduser(Config.get('host_dir'))
    dst_file_name = os.path.join(host_dir, local_file)
    with open(dst_file_name, 'wb') as dst_file:
        bytes_remaining = filesize
        write_buf = bytearray(BUFFER_SIZE)
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, BUFFER_SIZE)
            buf_remaining = read_size
            buf_index = 0
            while buf_remaining > 0:
                read_buf = device.read(buf_remaining)
                bytes_read = len(read_buf)
                if bytes_read:
                    write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                    buf_index += bytes_read
                    buf_remaining -= bytes_read
            dst_file.write((write_buf[0:read_size]))
            # Send an ack to the remote as a form of flow control
            device.write(b'\x06')   # ASCII ACK is 0x06
            bytes_remaining -= read_size


def _file_size(filepath):
    import os
    try:
        return os.stat(filepath)[6]
    except:
        return -1

# create directories recursively
def _makedirs(path):
    import os
    try:
        os.mkdir(path)
        return True
    except OSError as e:
        if e.args[0] == 2:
            # no such file or directory
            try:
                _makedirs(path[:path.rfind(os.sep)])
                os.mkdir(path)
            except:
                return False
    return True

# equivalent of rm -rf path
def _rm_rf(path, recursive):
    import os
    try:
        mode = os.stat(path)[0]
        if mode & 0x4000 != 0:
            # directory
            if recursive:
                for file in os.listdir(path):
                    success = _rm_rf(path + '/' + file, recursive)
                    if not success:
                        return False
                os.rmdir(path)
        else:
            os.remove(path)
    except:
        return False
    return True

def _cat(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            print(line, end="")
