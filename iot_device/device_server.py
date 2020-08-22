from .certificate import create_key_cert_pair
from .config_store import Config

import socket
import ssl
import threading
import json
import time
import tempfile
import logging

logger = logging.getLogger(__file__)


class DeviceServer():

    def __init__(self, discovery, max_age=5):
        # serve devices in discovery
        self.__discovery = discovery
        self.__max_age = max_age
        self.__ip = self.__my_ip()
        self.__ssl_context = self.__make_ssl_context()
        # start connection server
        th = threading.Thread(target=self.__device_server, name="Serve Devices")
        th.setDaemon(True)
        th.start()
        # start advertising deamon
        th = threading.Thread(target=self.__advertise, name="Advertise")
        th.setDaemon(True)
        th.start()

    def __device_server(self):
        # note: serving only a single connection at a time!
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = Config.get('connection_server_port')
        srv.bind(('', port))
        srv.listen()
        while True:
            logger.info(f"Accepting connections on {self.__ip}:{port}")
            client_socket, addr = srv.accept()
            logger.info(f"Connection from {client_socket} {addr}")
            client_socket = self.__ssl_context.wrap_socket(client_socket, server_side=True)
            # More quickly detect bad clients who quit without closing the
            # connection: After 1 second of idle, start sending TCP keep-alive
            # packets every 1 second. If 3 consecutive keep-alive packets
            # fail, assume the client is gone and close the connection.
            try:
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except AttributeError:
                pass  # not available on windows
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                # get uid and password
                uid_pwd = json.loads(client_socket.recv(1024).decode())
                uid = uid_pwd.get('uid', '?')
                logger.debug(f"Connection from {addr} to {uid}")
                # check password
                if uid_pwd.get('password') != Config.get('password'):
                    client_socket.write(b'wrong password')
                else:
                    device = self.__discovery.get_device(uid)
                    if not device:
                        client_socket.write(b'device not known')
                    else:
                        client_socket.write(b'ok')
                        self.__serve_device(device, client_socket)
            except Exception as e:
                # run "forever"
                logger.exception(f"{type(e).__name__} in __device_server: {e}")
            finally:
                logger.info(f"Disconnected {uid}")
                client_socket.close()

    def __serve_device(self, device, client_socket):
        client_socket.setblocking(False)
        while True:
            # client_socket --> device.write
            try:
                msg = client_socket.recv(256)
                if not len(msg): 
                    break
                device.write(msg)
            except ssl.SSLWantReadError:
                pass
            except ConnectionResetError:
                break
            # device.read_all --> client_socket
            msg = device.read_all()
            if len(msg) > 0: 
                client_socket.sendall(msg)

    def __advertise(self):
        s = None
        while True:
            logger.debug("__advertise start")
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                advertise_port = Config.get('advertise_port')
                self.__discovery.scan()
                with self.__discovery as devices:
                    for dev in devices:
                        if dev.age > self.__max_age: 
                            logger.debug(f"Not advertising {dev} due to age")
                            continue
                        msg = {
                            'uid': dev.uid,
                            'ip_addr': self.__ip,
                            'ip_port': Config.get('connection_server_port'),
                            'protocol': 'repl'
                        }
                        data = json.dumps(msg)
                        s.sendto(data.encode(), ('255.255.255.255', advertise_port))
                        logger.debug(f"Advertise {dev}")
            except Exception as e:
                # restart, e.g. in case of [Errno 51] Network is unreachable
                logger.exception(f"Error in advertise, restablishing connection: {e}")
                if s:
                    try:
                        s.close()
                    except:
                        pass
                time.sleep(5)
            time.sleep(max(1, self.__max_age-2))

    def __my_ip(self):
        # determine host's ip address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # fake address, does not need to be reachable
            s.connect(('10.1.1.1', 1))
            return s.getsockname()[0]

    def __make_ssl_context(self):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        with tempfile.NamedTemporaryFile() as cert_file:
            key, cert = create_key_cert_pair()
            cert_file.write(key)
            cert_file.write(cert)
            cert_file.seek(0)
            context.load_cert_chain(certfile=cert_file.name)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')
        return context



##########################################################################
# Main

def main():
    import sys
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(filename)s: %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    from .discover_serial import DiscoverSerial
    discover = DiscoverSerial()
    server = DeviceServer(discover)
    print("started server", server)

    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()