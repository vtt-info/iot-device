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


class ConnectionServer():

    def __init__(self, discovery, max_age=5):
        # serve devices in discovery
        self.__discovery = discovery
        self.__max_age = max_age
        self.__ip = self.__my_ip()
        self.__ssl_context = self.__make_ssl_context()
        # start connection server
        th = threading.Thread(target=self.__connection_server, name="Serve Connections")
        th.setDaemon(True)
        th.start()
        # start advertising deamon
        th = threading.Thread(target=self.__advertise, name="Advertise")
        th.setDaemon(True)
        th.start()

    def __connection_server(self):
        # note: serving only a single connection at a time!
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = Config.get('connection_server_port')
        srv.bind(('', port))
        srv.listen()
        try:
            while True:
                with self.__discovery as devices:
                    sz = len(devices)
                logger.info(f"Waiting for connections on {self.__ip}:{port} to {sz} devices")
                client_socket, addr = srv.accept()
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
                    if uid_pwd.get('pwd') != Config.get('password'):
                        client_socket.write(b'wrong password')
                    else:
                        device = self.__discovery.get_device(uid)
                        if not device:
                            client_socket.write(b'device not known')
                        else:
                            client_socket.write(b'ok')
                            self.__serve_device(device, client_socket)
                finally:
                    ser2net.socket = None
                    logger.info(f"Disconnected {device}")
                    client_socket.close()
        except KeyboardInterrupt:
            pass
        except ConnectionAbortedError:
            logger.info(f"ConnectionAbortedError for {device}")
        except IOError as ioe:
            logger.info(f"IOError for {device}: {ioe}")
        finally:
            logger.info(f"Exit serving {device}")
            serial_worker.stop()
            with self.serving_lock:
                del self.serving[device]

    def __serve_device(self, device, client_socket):
        pass
        # start network <--> serial loop
        ser2net.socket = client_socket
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                for i in range(0, len(data), 256):
                    ser.write(data[i:min(i+256, len(data))])
                    # give VM a little time to catch up
                    time.sleep(0.01)
            except socket.error as msg:
                logger.info(f"Socket error for {device}: {msg}")
                break

    def __advertise(self):
        s = None
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                advertise_port = Config.get('advertise_port')
                logger.debug(f"advertise on port {advertise_port}")
                with self.__discovery as devices:
                    for dev in devices:
                        if dev.age > self.__max_age: continue
                        msg = {
                            'uid': dev.uid,
                            'ip_addr': self.__ip,
                            'ip_port': Config.get('connection_server_port'),
                            'protocol': 'repl'
                        }
                        data = json.dumps(msg)
                        s.sendto(data.encode(), ('255.255.255.255', advertise_port))
                        logger.debug(f"Advertise {dev} as {data}")
                time.sleep(max(1, self.__max_age-2))
            except Exception as e:
                # restart, e.g. in case of [Errno 51] Network is unreachable
                logger.exception(f"Error in advertise, restablishing connection: {e}")
                if s:
                    try:
                        s.close()
                    except:
                        pass
                time.sleep(5)

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


class Serial2Net:

    def _replicate(self, device, description, baudrate=115200):
        # determine uid
        logger.info(f"compatible {device}")
        with SerialRepl(device, baudrate=baudrate) as sr:
            uid = ReplOps(sr).uid()
        logger.info(f"compatible {uid}")
        # open serial port
        ser = serial.serial_for_url(device, do_not_open=True)
        ser.baudrate = baudrate
        ser.open()
        # start socket server
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('', 0))
        port = srv.getsockname()[1]
        # start reader thread
        ser2net = _SerialToNet(device, srv)
        serial_worker = serial.threaded.ReaderThread(ser, ser2net)
        serial_worker.start()

        # start serving
        mcu = MCU(uid, ip_addr=self.ip, ip_port=port, description=description)
        logger.info(f"serve {mcu}")
        with self.serving_lock:
            self.serving[device] = mcu
        th = threading.Thread(target=self._serve, name=f"Serve {device}",
            args=(device, ser, srv, ser2net, serial_worker))
        th.setDaemon(True)
        th.start()



class _SerialToNet(serial.threaded.Protocol):
    """serial->socket"""

    def __init__(self, device, srv):
        self.socket = None
        self.device = device
        self.srv = srv

    def __call__(self):
        return self

    def data_received(self, data):
        if self.socket is not None:
            try:
                self.socket.sendall(data)
            except BrokenPipeError as e:
                logger.error(f"Broken pipe in _SerialToNet: {e}")
                self.socket.close()
                # abort srv.accept in _serve
                self.srv.close()

    def connection_lost(self, exc):
        logger.info(f"Serial port {self.device} disconnected")
        # abort srv.accept in _serve
        self.srv.close()


#####################################################################

def main():
    logger.info("serial2net.main starting ...")
    serial2net = Serial2Net()
    serial2net.scan()

if __name__ == "__main__":
    main()
