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
import logging, time, socket, select, json, types, typing, \
    itertools, os, functools, collections, uuid, time
log = logging.getLogger('synchc')
logging.basicConfig(level=logging.INFO)

from .detect import detect, Endpoint

nonempty = lambda lst: [x for x in lst if x]

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


class RemoteError(Exception):
    """
    A RemotError represents a returned error message by the endpoint.
    Typically this means the LUCIDAC HybridController could not decode a message,
    there is some typing or logic problem.
    
    The error message from the server always contains an integer error code and
    a human readable string error message.
    
    In order to trace the error at the firmware side, both the code and string
    can be helpful. You can grep the firwmare code with the string. For the code,
    you have to understand how they are computed server side or consult the
    firmware documentation.
    """
    def __init__(self, recv_envelope):
        self.code = recv_envelope.code
        self.type = recv_envelope.type
        self.raw = recv_envelope
        super().__init__(f"Remote error {recv_envelope.code} at query {recv_envelope.type}: '{recv_envelope.error}'")


class LocalError(ValueError):
    """
    A LocalError represents a logic flaw at the client side, i.e. within the lucipy
    code. It did not expect some message from the server or could not deserialize
    messages received.
    
    Note that next to LocalErrors you can always receive things such as SocketError,
    OSError or similiar low level connection problems (for instance: OSError "no route
    to host")
    """
    pass

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
            print(f"tcpsocket.send({sth=})")
            #self.s.sendall(sth.encode("ascii"))
            self.fh.write(sth + "\n")
            self.fh.flush()
            #print("tcpsocket.send() completed")
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"tcpsocket.send: {e}")
            if self.auto_reconnect:
                self.connect()
                return self.send(sth)
            else:
                raise e
    def read(self, *args, **kwargs):
        "Returns a complete line as string. See instead also: self.s.recv(123)"
        try:
            #print("tcpsocket.readline()")
            #import ipdb; ipdb.set_trace()
            line = self.fh.readline()
            print(f"tcpsocket.read() = {line}")
            return line
        except UnicodeDecodeError as e:
            print(e)
            return ""
        except ConnectionResetError as e:
            print(f"tcpsocket.read: {e}")
            if self.auto_reconnect:
                self.connect()
                return "" # empty line, since query protcol should not readline empty socket
            else:
                raise e
    def has_data(self):
        return has_data(self.s)
    def __repr__(self):
        return f"tcp://{self.host}:{self.port}"
    
# TODO: Probably refactor code, the classes tcpsocket and serialsocket share most of their logic

class serialsocket:
    "Uses pyserial to connect to directly attached device"
    def __init__(self, device):
        if not serial:
            raise ImportError("PySerial not available, please install with 'pip install pyserial'")
        self.device = device
        self.fh = serial.Serial(self.device)
        # sometimes there is stuff stuck in the serial port. Read all of it and wipe it.
        while self.has_data():
            self.fh.readline()
    def close(self):
        self.fh.close()
    def send(self, sth):
        #print(f"serialsocket.send({sth})")
        self.fh.write(sth.encode("ascii") + b"\n")
        self.fh.flush()
        #print(f"serialsocket.send completed")
    def read(self):
        # block until have read exactly one line
        while self.has_data():
            ret = self.fh.readline()
            #print(f"serialsocket.read(): {ret}")
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
        #print(f"jsonlines.send({json.dumps(sth)}")
        self.sock.send(json.dumps(sth))
        #print(f"jsonlines.send completed")
    def read(self, *args, **kwargs):
        #print("jsonlines.read()")
        read = self.sock.read(*args, **kwargs)
        while not read:
            print("haven't read anything, trying again")
            time.sleep(0.2)
            read = self.sock.read(*args, **kwargs)
        #print(f"jsonlines.read() got {read}")
        try:
            return json.loads(read)
        except json.JSONDecodeError as s:
            raise LocalError(f"Could not decode as JSON: {s}. Received message ({len(read)} characters) is '{read}'")
    def read_all(self):
        while self.sock.has_data():
            yield self.read()

def endpoint2socket(endpoint_url: typing.Union[Endpoint,str]) -> typing.Union[tcpsocket,serialsocket]:
    "Provides the appropriate socket for a given endpoint"
    endpoint = Endpoint(endpoint_url)
    if endpoint.asDevice(): # serial:/dev/foo
        return serialsocket(endpoint.asDevice())
    elif endpoint.asURL().scheme == "tcp": # tcp://192.168.1.2:5732
        url = endpoint.asURL()
        tcp_port = endpoint.default_tcp_port if not url.port else url.port
        return tcpsocket(url.hostname, tcp_port) # TODO: Get auto_reconnect from a query string
    else:
        raise ValueError(f"Illegal {endpoint_url=}. Expecting something like tcp://192.168.1.2:5732 or serial:/dev/foo")


class Run:
    "Represents a running Run"
    run_states = "DONE ERROR IC NEW OP OP_END QUEUED TAKE_OFF TMP_HALT".split()
    
    def __init__(self, hc):
        self.hc = hc
    
    def next_data(self) -> typing.Iterator[typing.List[float]]:
        """
        Reads next dataset from DAQ (data aquisiton) which is streamed during the run.
        A call to this function yields a single dataset once arrived. It returns
        when the run is finished and raises a LocalError if it doesn't properly
        stop.
    
        The shape of data returned by this call is determined by the requested number
        of DAQ channels, which is between 0 (= no data will be returned at all, not
        even an empty directory per dataset) and 8 (= all channels). That is, the
        following invariant holds:
    
        >>> lines = run.next_data()                                                    # doctest: +SKIP
        >>> assert all(hc.daq_config["num_channels"] == len(line) for line in lines)   # doctest: +SKIP
    
        This invariant is also asserted within the method.
        """
        envelope = self.hc.sock.read()
        if envelope["type"] == "run_data":
            # TODO check for proper run id and entity.
            msg_data = envelope["msg"]["data"]
            assert all(self.hc.daq_config["num_channels"] == len(line) for line in msg_data)
            yield msg_data
        elif envelope["type"] == "run_state_change":
            msg_old = envelope["msg"]["new"]
            msg_new = envelope["msg"]["new"]
            if msg_new == "DONE":
                return # successfully transfered all data
            if msg_new == "ERROR":
                raise LocalError(f"Could not properly start the run. Most likely the DAQ ({self.hc.daq_config}) or RUN ({self.hc.run_config}) configuration not accepted by the server side.")
            # Attention: After runstate stop there still can come a last data
            #            package.
        else:
            raise LocalError(f"Run::slurp(): Unexpected message {envelope}")
            #return # stop slurping

    def data(self) -> typing.List[float]:
        """
        Returns all measurement data (evolution data on the ADCs) during a run.
        
        This is basically a synchronous wait until the run finishes.
        
        The shape of data returned by this call is basically
        ``NUM_SAMPLING_POINTS x NUM_CHANNELS``. Since this is a uniform array, users
        can easily use numpy to postprocess and extract what they are interested in.
        Typically, you want to trace the evolution of particular channels, for instance
        
        >>> data = np.array(run.data())                      # doctest: +SKIP
        >>> x, y, z = data[:,0], data[:,1], data[:,2]        # doctest: +SKIP
        >>> plt.plot(x)                                      # doctest: +SKIP
    
        See also :meth:`next_data` and example application codes.
        """
        ret = []
        for lines in self.next_data():
            ret += lines
        return ret

class LUCIDAC:
    """
    This kind of class is known as *HybridController* in other codes. It serves as
    primary entry point for the lucipy code.
        
    The constructor has a variety of variants how to be called:
        
    :param endpoint_url: If no endpoint (either as string or Endpoint class instance)
        is provided, will lookup the environment variable ``LUCIDAC_ENDPOINT``. 
        
        If neither an endpoint nor the environment variable is set, autodetection
        is applied and the first connection is chosen. Note that if no LUCIDAC
        is attached via USB serial, the zeroconf detection will require a few
        hundred milliseconds, depending on your network.
    :param auto_reconnect: Whether reconnect in case of los connection
    :param register_methods: Register typical message types exposed by the server
        as methods for this class. This allows to call ``hc.foo(bar)`` instead of
        ``hc.query("foo", bar)``.
    """
   
    ENDPOINT_ENV_NAME = "LUCIDAC_ENDPOINT"
    
    # a list of commands which will be exposed as methods, for shorthands.

    # TODO: Maybe write more verbose as in pyanalog in order to have a more usable documentation!
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
    memoizable = "sys_ident".split()
    
    def __init__(self, endpoint_url=None, auto_reconnect=True, register_methods=True):
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
        
        "Eth Mac address of Microcontroller, required for the circuit entity hierarchy"
        self.hc_mac = None
        # TODO: Maybe change firmware once in a way that it doesn't really need the client to know it
        
        "Storage for stateful preparation of runs."
        self.run_config = dotdict(
            halt_on_external_trigger = False,
            halt_on_overload  = True,
            ic_time = 123456, # ns 
            op_time = 234567, # ns
        )

        "Storage for stateful preparation of runs."
        self.daq_config = dotdict(
            num_channels = 0,
            sample_op = True,
            sample_op_end = True,
            sample_rate = 500_000,
        )
        
        if register_methods:
            self.register_methods(self.commands, self.memoizable)
    
    @classmethod
    def _register_methods(cls, commands, memoizable=[], overwrite=False):
        """
        register method shorthands. Typically this method is only used by __init__.
        """
        for cmd in commands:
            shorthand = (lambda cmd: lambda self, msg={}: self.query(cmd, msg))(cmd)
            shorthand.__doc__ = f'Shorthand for ``query("{cmd}", msg)``, see :meth:`query`.'
            #shorthand = types.MethodType(shorthand, self) # bind function
            if cmd in memoizable:
                shorthand = functools.cache(shorthand)
            if not hasattr(cls, cmd) or overwrite:
                setattr(cls, cmd, shorthand)
    
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
            raise RemoteError(resp)
        if resp.type == envelope.type:
            # Do not show the empty message, in case of success.
            return resp.msg if resp.msg != {} else None
        else:
            log.error(f"req(type={envelope.type}) received unexpected: {resp=}")
            return resp
    
    def slurp(self):
        """
        Flushes the input buffer in the socket.
        
        Returns all messages read as a list. This is useful when we lost the remote
        state (wrongly tracked) and have to clean up.
    
        .. note::
        
           Calling this method should not be possible in regular usage. In particular, TCP
           connections are normally "clean". In contrast, serial terminals are ephermal
           from the Microcontrollers point of view, so it might be neccessary to flush
           the connection in particular at beginning of a connection.
        """
        return list(self.sock.read_all())
    
    def get_mac(self):
        "Get system ethernet mac address. Is cached."
        if not self.hc_mac:
            self.get_entities()
        return self.hc_mac
    
    def get_entities(self):
        "Gets entities and determines system Mac address"
        entities = self.query("get_entities")["entities"]
        mac = list(entities.keys())[0]
        # todo, assert that all this went fine, i.e. no KeyErrors or similar
        assert self.hc_mac == None or mac == self.hc_mac, "Inconsistent device mac"
        self.hc_mac = mac
        return entities

    @staticmethod
    def determine_idal_ic_time_from_k0s(mIntConfig):
        """
        Given a MIntBlock configuration, which looks like ``[{k:1000,ic:...},{k:10000,ic:...}...]``,
        determines the ideal ic time, in nanoseconds
        """
        def isFast(k0):
            fast_k0 = 10_000
            slow_k0 =    100
            if k0 == fast_k0: return True
            if k0 == slow_k0: return False
            else:             return True # is default at firmware side
        
        fast_ic_time =    100_000 # 100 us in ns
        slow_ic_time = 10_000_000 #  10 ms in ns
        areKfast = [ isFast(intConfig.get("k",None)) for intConfig in mIntConfig ]
        return fast_ic_time if all(areKfast) else slow_ic_time
    
    def _set_config_rev0_or_1(self, outer_config):
        # todo: Should determine before which is the correct call, for instance by
        #       evaluating what help() returns.
        try:
            return self.query("set_config", outer_config)
        except RemoteError as e:
            if e.code == -10:
                return self.query("set_circuit", outer_config)
            else:
                raise e
    
    def set_config(self, config):
        """
        config being something like ``dict("/U": ..., "/C": ...)``, i.e. the entities
        for a single cluster. There is only one cluster in LUCIDAC.
        
        .. warning::
        
           This also determines the ideal IC time *if* that has not been set
           before (either manually or in a previous run).
        """
        cluster_index = 0
        outer_config = {
            "entity": [self.get_mac(), str(cluster_index)],
            "config": config
        }
        #print(outer_config)
        
        if "/M0" in config and not "ic_time" in self.run_config:
            self.run_config.ic_time = self.determine_idal_ic_time_from_k0s(config["/M0"])
        
        return self._set_config_rev0_or_1(outer_config)
        
    
    def set_circuit(self, circuit):
        "set_config was renamed to set_circuit in later firmware versions"
        return self.set_config(circuit)
    
    def set_by_path(self, path, config):
        """
        Set element configuration by path.
        
        This is a fine-granular alternative to :meth:`set_circuit`.
        
        .. warning::
        
           Attention, this is ON THE CARRIER, i.e. the path relative to the carrier.
           Note that not all entities are on the carrier, such as the front panel!
        
        path is a string like ``["C", "17", "factor"]``
        
        .. note::
        
           Note that the path typically does NOT include something like "/C" or "/M0"
           but rather "C" or "M0".
        
        Example:
        
        >>> config = hc.get_config()["config"]["/0"]  # doctest: +SKIP
        >>> hc.set_by_path(["M0"], config["/M0"])     # doctest: +SKIP
        """
        cluster_index = 0
        outer_config = {
            "entity": [self.get_mac(), str(cluster_index)] + path,
            "config": config
        }
        return self._set_config_rev0_or_1(outer_config)
    
    def set_leds(self, leds_as_integer):
        # Cannot use set_circuit because it operates only on th Carrier
        return self._set_config_rev0_or_1({"entity": [self.get_mac(), "FP" ], "config": { "leds": leds_as_integer } })
        
    def signal_generator(self, dac=None):
        """
        :args dac: Digital analog converter outputs, as there are two a list with two floats (normalized [-1,+1]) is expected
        """
        return self._set_config_rev0_or_1({"entity": [self.get_mac(), "FP" ], "config": {
            "signal_generator":  { "dac_outputs": dac, "sleep": False }
        } })
    
    def set_op_time(self, *, ns=0, us=0, ms=0):
        """
        Sets OP-Time with clear units. Returns computed value, which is just the **sum of
        all arguments**.
        
        Consider the limitations reported in :meth:`start_run`.
        
        Note that this function signature is somewhat comparable to python builtin
        `datetime.timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_,
        however Python's timedelta has only microseconds resolution which is not as
        highly-resolved as in LUCIDAC.
        
        
        :param ns: nanoseconds
        :param us: microseconds
        :param ms: milliseconds
        """
        self.run_config.op_time = ns + us*1000 + ms*1000*1000
        return self.run_config.op_time
    
    #: Sample rates per second accepted by the system.
    allowed_sample_rates = [1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 80, 100, 125, 160, 200, 250, 320, 400, 500, 625, 800, 1000, 1250, 1600, 2000, 2500, 3125, 4000, 5000, 6250, 8000, 10000, 12500, 15625, 20000, 25000, 31250, 40000, 50000, 62500, 100000, 125000, 200000, 250000, 500000, 1000000]
    
    def set_daq(self, *,
            num_channels = 0,
            sample_op = True,
            sample_op_end = True,
            sample_rate = 500_000,
            ):
        """
        :param num_channels: Data aquisition specific - number of channels to sample. Between
           0 (no data aquisition) and 8 (all channels)
        :param sample_op: Sample a first point exactly when optime starts
        :param sample_op_end: Sample a last point exactly when optime ends
        :param sample_rate: Number of samples per second. Note that not all numbers are
           supported. A client side check is performed.
        """
        if not (0 <= num_channels and num_channels < 8):
            raise ValueError("Require 0 <= num_channels < 8")
        # TODO: Check also other values for suitable value.
        # Do it here or at start_run just before query.

        self.daq_config.num_channels = num_channels
        self.daq_config.sample_op = sample_op
        self.daq_config.sample_op_end = sample_op_end
        
        if not sample_rate in self.allowed_sample_rates:
            raise ValueError(f"{sample_rate=} not allowed. Only values allowed from the following list: {allowed_sample_rates}")
        
        self.daq_config.sample_rate = sample_rate
       
        return self.daq_config

    def set_run(self, *,
            halt_on_external_trigger = False,
            halt_on_overload = True,
            ic_time = None,
            op_time = None,
            ):
        """
        :param halt_on_external_trigger: Whether halt the run if external input triggers
        :param halt_on_overload: Whether halt the run if overload occurs during computation
        :param ic_time: Request time to load initial conditions, in nanoseconds.
           This time depends on the k0 factors. However, it is rarely neccessary to tune this
           parameter, once useful values have been used. If not set, a value derived from the
           (first time in object lifetime) configuration set will be used.
        :param op_time: Request time for simulation, in nanoseconds. This is the most important
           option for this method. Note that by a current limitation in the hardware, only
           op_times < 1sec are supported.
        """
        self.run_config.halt_on_external_trigger = halt_on_external_trigger
        self.run_config.halt_on_overload = halt_on_overload
        if ic_time:
            self.run_config.ic_time = ic_time
        if op_time:
            self.run_config.op_time = op_time
        return self.run_config

    def start_run(self) -> Run:
        """
        Uses the set_run and set_daq as before.
        Returns a Run object which allows to read all data.
        """

        start_run_msg = dict(
            id = str(uuid.uuid4()),
            session = None,
            config = self.run_config,
            daq_config = self.daq_config
        )
        
        self.slurp() # slurp old run data or similar
        ret = self.query("start_run", start_run_msg)
        if ret:
            raise LocalError(f"Run did not start successfully. Expected answer to 'start_run' but got {ret=}")
    
        return Run(self)
    
    def manual_mode(self, to:str):
        "manual mode control"
        return self.query("manual_mode", dict(to=to))
    
    def master_for(self, *minions):
        """
        Create a master-minion setup with at least one controlled LUCIDAC (minion).
        minions: type LUCIDAC
        """
        return LUCIGroup(self, *minions)

LUCIDAC._register_methods(LUCIDAC.commands)

class LUCIGroup:
    """
    Group of LUCIDACs in a master/minion setup. Usage is like
        
    >>> gru    = LUCIDAC("tcp://foo")       # doctest: +SKIP
    >>> kevin  = LUCIDAC("tcp://bar")       # doctest: +SKIP
    >>> bob    = LUCIDAC("tcp://baz")       # doctest: +SKIP
    >>> group  = LUCIGroup(gru, kevin, bob) # doctest: +SKIP
    >>> group.set_circuit(...)              # doctest: +SKIP
    >>> group.start_run() ...               # doctest: +SKIP
    """
    
    def __init__(self, master: LUCIDAC, *minions: LUCIDAC):
        self.master = master
        self.minions = minions
        for minion in self.minions:
            res = minion.manual_mode("minion")
            if res:
                raise ValueError(f"Failed to make {minion} a minion, returned {res}")
    
    def __getattr__(self, attr):
        if attr not in self.__dict__:
            # for the moment, we forward every command only to the master.
            # Later, we want to collect results, such as from "get_entities".
            # However, in the moment this does not even work on free floating teensies with
            # LUCIDAC REV1 hardware, cf. hybrid-controller#145.
            return getattr(self.master, attr)
        
    
    

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
