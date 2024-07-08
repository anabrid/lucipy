#!/usr/bin/env python3

"""
An Synchronous Hybrid Controller Python Client for REDAC/LUCIDAC

This is a minimal python client, making simple things simple. That means things
like device managament is capable of the python REPL without headache, following
the KISS principle.

This client implementation does *not* feature strong typing, dataclasses,
asynchronous functions. Instead, it implements a blocking API and tries to
mimic the way how the Model-1 Hybrid Controller interface worked
(the one in https://github.com/anabrid/pyanalog/).

This is a single file implementation focussing on portability and minimal
dependencies. If you have pyserial installed, it will be used, otherwise this
also runs fine without.
"""

# all this is only python standard library  :)
import logging, time, socket, select, json, types, \
    itertools, os, functools, collections
log = logging.getLogger('synchc')
logging.basicConfig(level=logging.INFO)

from .detect import detect, Endpoint


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
    "Peeks a file handle (checks for data without reading/consuming)"
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
            #print(f"Have read: {ret}")
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
        read = self.sock.read(*args, **kwargs)
        if not read:
            print("haven't read anything, trying again")
            read = self.sock.read(*args, **kwargs)

        return json.loads(read)
        #except json.JSONDecodeError as s:
    def read_all(self):
        while self.sock.has_data():
            yield self.read()

class HybridControllerError(Exception):
    pass

def endpoint2socket(endpoint_url:Endpoint|str) -> tcpsocket|serialsocket:
    endpoint = Endpoint(endpoint_url)
    if endpoint.asDevice(): # serial:/dev/foo
        return serialsocket(endpoint.asDevice())
    elif endpoint.asURL().scheme == "tcp": # tcp://192.168.1.2:5732
        url = endpoint.asURL()
        tcp_port = endpoint.default_tcp_port if not url.port else url.port
        return tcpsocket(url.hostname, tcp_port) # TODO: Get auto_reconnect from a query string
    else:
        raise ValueError(f"Illegal {endpoint_url=}. Expecting something like tcp://192.168.1.2:5732 or serial:/dev/foo")

class LUCIDAC:
    """
    This kind of class is known as *HybridController* in other codes.
    """
    
    ENDPOINT_ENV_NAME = "LUCIDAC_ENDPOINT"
    # a list of commands which will be exposed as methods, for shorthands.
    commands = """
        ping help
        reset_circuit set_circuit get_circuit
        get_entities
        start_run
        one_shot_daq
        manual_mode
        net_get net_set net_reset net_status
        login
        lock_acquire lock_release
        sys_ident sys_reboot
    """.split()
    
    # Commands which can be memoized for a given endpoint/instance, makes
    # it cheaper to call them repeatedly
    memoizable = "get_entities sys_ident".split()
    
    
    def __init__(self, endpoint_url=None, auto_reconnect=True, register_methods=True):
        """
        If no endpoint is given but the environment variable LUCIDAC_ENDPOINT
        is set, this value is used.
    
        If neither an endpoint nor the environment variable is set, autodetection
        is applied and the first connection is chosen. Note that if no LUCIDAC
        is attached via USB serial, the zeroconf detection will require a few
        hundred milliseconds, depending on your network.        """
        if not endpoint_url:
            if self.ENDPOINT_ENV_NAME in os.environ:
                endpoint_url = os.environ[self.ENDPOINT_ENV_NAME]
            else:
                endpoint_url = detect(single=True)
                if not endpoint_url:
                    raise ValueError("No endpoint provided as argument or in ENV variable and could also not discover something on USB or in Network.")
                
        socket = endpoint2socket(endpoint_url)
        self.sock = jsonlines(socket)
        self.req_id = 50
        
        if register_methods:
            self.register_methods(self.commands, self.memoizable)
        
    def register_methods(self, commands, memoizable=[]):
        # register commands
        for cmd in commands:
            shorthand = (lambda cmd: lambda self, msg={}: self.query(cmd, msg))(cmd)
            shorthand.__doc__ = f'Shorthand for query("{cmd}", msg)'
            shorthand = types.MethodType(shorthand, self) # bind function
            setattr(self, cmd, functools.cache(shorthand) if cmd in memoizable else shorthand)
    
    def __repr__(self):
        return f"LUCIDAC(\"{self.sock.sock}\")"
    
    def send(self, msg_type, msg={}):
        "Sets up an envelope and sends it, but does not wait for reply"
        envelope = dict(id=self.req_id, type=msg_type, msg=msg)
        self.req_id += 1
        self.sock.send(envelope)
        return envelope

    def query(self, msg_type , msg={}):
        "Sends a query and waits for the answer, returns that answer"
        envelope = dotdict(self.send(msg_type, msg))
        resp = dotdict(self.sock.read())
        if envelope == resp:
            # This is a serial socket replying first what was typed. Read another time.
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
    hc = LUCIDAC(args.endpoint)
    
    import IPython
    IPython.embed()
    
# Other simple example:
#    hc = HybridController("192.168.68.60", 5732)
#    status = hc.query('status')
#    print(status)
