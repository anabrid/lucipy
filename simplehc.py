
import logging, time, socket, json, types # builtins
log = logging.getLogger('simplehc')
logging.basicConfig(level=logging.INFO)

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    #__getattr__ = dict.get
    def __getattr__(*args):
        val = dict.__getitem__(*args)
        return dotdict(val) if type(val) is dict else val
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


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
    def read(self):
        "Returns a complete line as string. See instead also: self.s.recv(123)"
        try:
            return self.fh.readline() 
        except ConnectionResetError:
            if self.auto_reconnect:
                self.connect()
                return "" # empty line, since query protcol should not readline empty socket

class jsonlines(tcpsocket):
    "A socket that speaks dictionaries at front and JSON at back"
    def __init__(self, *args, **kwargs):
        super(jsonlines, self).__init__(*args, **kwargs)
    #def __init__(self, *tcpopts, **tcpkvopts):
    #    self.sock = tcpsocket(*tcpopts, **tcpkvopts)
    def send(self, sth):
        super().send(json.dumps(sth))
    def read(self):
        #try:
        return json.loads(super().read())
        #except json.JSONDecodeError as s:
        
class HybridControllerError(Exception):
    pass

class HybridController:
    def __init__(self, host, port, auto_reconnect=True):
        self.sock = jsonlines(host, port, auto_reconnect)
        self.req_id = 50
    def __repr__(self):
        return f"HybridController({self.sock.host},{self.sock.port})"
    
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
            raise HybridControllerError(resp['error'])
        if resp.type == envelope.type:
            return resp.msg
        else:
            log.error(f"req(type={envelope.type}) received unexpected: {resp=}")
            return resp

if __name__ == "__main__":
    # simple example demonstrator
    hc = HybridController("192.168.68.60", 5732)
    status = hc.query('status')
    print(status)
