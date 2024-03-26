#!/usr/bin/env python3

import logging, time, socket, select, json, types, itertools, urllib # builtins
log = logging.getLogger('simplehc')
logging.basicConfig(level=logging.INFO)

try:
    import serial
except ModuleNotFoundError:
    serial = None

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    #__getattr__ = dict.get
    def __getattr__(*args):
        val = dict.__getitem__(*args)
        return dotdict(val) if type(val) is dict else val
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def has_data(fh):
    rlist, wlist, xlist = select.select([fh], [],[], 0)
    return len(rlist) != 0


class tcpsocket:
    "A socket with readline support"
    def __init__(self, host, port, auto_reconnect=True):
        self.host, self.port, self.auto_reconnect = host, port, auto_reconnect
        self.connect()
    def connect(self):
        if(hasattr(self, 's')):
            log.warning(f"Trying to reconnect to {self.host}:{self.port}...")
        else:
            log.info(f"Connecting to TCP {self.host}:{self.port}...")
        self.s = socket.socket()
        self.s.connect((self.host,self.port))
        self.fh = self.s.makefile(mode="rw", encoding="utf-8")
    def close(self):
        self.s.close()
        del self.s
    def send(self, sth):
        "Expects sth to be a string"
        try:
            self.s.sendall(sth.encode("ascii"))
        except ConnectionResetError:
            if self.auto_reconnect:
                self.connect()
                return self.send(sth)
    def read(self, *args, **kwargs):
        "Returns a complete line as string. See instead also: self.s.recv(123)"
        try:
            return self.fh.readline() 
        except ConnectionResetError:
            if self.auto_reconnect:
                self.connect()
                return "" # empty line, since query protcol should not readline empty socket
    def has_data(self):
        return has_data(self.s)
    def __repr__(self):
        return f"tcp://{self.host}:{self.port}"
    
class serialsocket:
    "Uses pyserial to connect to directly attached device"
    def __init__(self, device):
        if not serial:
            raise Error("PySerial not available, please install with 'pip install pyserial'")
        self.device = device
        self.fh = serial.Serial(self.device)
        # sometimes there is stuff stuck in the serial port. Read all of it and wipe it.
        while self.has_data():
            self.fh.readline()
    def close(self):
        self.fh.close()
    def send(self, sth):
        self.fh.write(sth.encode("ascii") + b"\n")
    def read(self):
        # block until have read exactly one line
        while self.has_data():
            ret = self.fh.readline()
            print(f"Have read: {ret}")
            return ret
    def has_data(self):
        return has_data(self.fh)
    def __repr__(self):
        return f"socket:/{self.device}"

class jsonlines():
    "Middleware that speaks dictionaries at front and JSON at back"
    def __init__(self, actual_socket):
        self.sock = actual_socket
    @staticmethod
    def makeSocket(cls, actual_socket_type, *args, **kwargs):
        return cls(actual_socket_type(*args, **kwargs))
    def send(self, sth):
        self.sock.send(json.dumps(sth))
    def read(self, *args, **kwargs):
        #try:
        return json.loads(self.sock.read(*args, **kwargs))
        #except json.JSONDecodeError as s:
    def read_all(self):
        while self.sock.has_data():
            yield self.read()

class HybridControllerError(Exception):
    pass

class HybridController:
    def __init__(self, endpoint_url, auto_reconnect=True):
        url = urllib.parse.urlparse(endpoint_url)
        if url.scheme == "tcp": # tcp://192.168.1.2:5732
            socket = tcpsocket(url.hostname, url.port, auto_reconnect)
        elif url.scheme == "serial": # serial:/dev/foo
            socket = serialsocket(url.path)
        else:
            raise ValueError(f"Illegal {endpoint_url=}. Expecting something like tcp://192.168.1.2:5732 or serial:/dev/foo")
        self.sock = jsonlines(socket)
        self.req_id = 50
    
    def __repr__(self):
        return f"HybridController(\"{self.sock.sock}\")"
    
    def send(self, msg_type, msg={}):
        "Sets up an envelope and sends it, but does not wait for reply"
        envelope = dict(id=self.req_id, type=msg_type, msg=msg)
        self.req_id += 1
        self.sock.send(envelope)
        return envelope

    def query(self, msg_type , msg={}):
        envelope = dotdict(self.send(msg_type, msg))
        resp = dotdict(self.sock.read())
        if "error" in resp:
            raise HybridControllerError(resp)
        if resp.type == envelope.type:
            # Do not show the empty message, in case of success.
            return resp.msg if resp.msg != {} else None
        else:
            log.error(f"req(type={envelope.type}) received unexpected: {resp=}")
            return resp
    
    def slurp(self):
        return list(self.sock.read_all())
             

if __name__ == "__main__":
    # simple example demonstrator
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", help="Lucidac endpoint URL (such as tcp:/192.168.1.1:5732 or serial:/dev/ttyACM0)")
    args= parser.parse_args()
    hc = HybridController(args.endpoint)
    
    import IPython
    IPython.embed()
    
# Other simple example:
#    hc = HybridController("192.168.68.60", 5732)
#    status = hc.query('status')
#    print(status)
