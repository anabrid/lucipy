#!/usr/bin/env python3

"""
An Synchronous Hybrid Controller Python Client for REDAC/LUCIDAC.

This is a minimal python client with focus on interactive python prompt usage.

This client implementation does *not* feature strong typing, dataclasses,
asynchronous functions. Instead, it implements a blocking API and tries to
mimic the way how the *Model-1 Hybrid Controller* interface worked
(in particular in the `PyAnalog <https://github.com/anabrid/pyanalog/>`_
research code).

This is a single file implementation focussing on portability and minimal
dependencies. If you have ``pyserial`` installed, it will be used to allow
serial connections, otherwise it runs with python "batteries included" to
connect to TCP/IP targets.

In particular, there are no dependencies on any other lucipy module, except
:mod:`~lucipy.detect`. In particular, this code is completely independent from
the :mod:`~lucipy.circuits` module which can serve to simplify to set up the
data structure required by :meth:`LUCIDAC.set_circuit`.

The main class to use from this module is :class:`LUCIDAC`.
"""

# all this is only python standard library  :)
import logging, time, socket, select, json, types, typing, \
    itertools, os, functools, collections, uuid, time
log = logging.getLogger('synchc')
logging.basicConfig(level=logging.INFO)

from .detect import detect, Endpoint

__all__ = """
    LUCIDAC Run LUCIGroup
    RemoteError LocalError
""".split()

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
        self.debug_print = False
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
        return self.s.close()
        #del self.s
    def send(self, sth):
        "Expects sth to be a string"
        try:
            if self.debug_print:
                print(f"tcpsocket.send({sth=})")
            #self.s.sendall(sth.encode("ascii"))
            self.fh.write(sth + "\n")
            self.fh.flush()
            #print("tcpsocket.send() completed")
        except (BrokenPipeError, ConnectionResetError) as e:
            if self.debug_print:
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
            if self.debug_print:
                print(f"tcpsocket.read() = {line}")
            return line
        except UnicodeDecodeError as e:
            print(e)
            return ""
        except ConnectionResetError as e:
            if self.debug_print:
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
        return self.fh.close()
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

class emusocket:
    "Emulates a socket with a callback function"
    def __init__(self, callback=None, debug=False):
        if not callback:
            from .simulator import Emulation
            emu = Emulation(debug=debug)
            callback = lambda line: emu.handle_request(line)
        self.callback = callback
        self.return_buffer = []
    def send(self, sth):
        ret = self.callback(sth)
        if isinstance(ret, list):
            self.return_buffer += ret
        else:
            self.return_buffer.append(ret)
    def read(self):
        if self.has_data():
            return self.return_buffer.pop(0)
    def close(self):
        pass
    def has_data(self):
        return len(self.return_buffer)
    def __repr__(self):
        return f"emu:/?callback={self.callback}"

class jsonlines:
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
    def close(self):
        return self.sock.close()
    def read_all(self):
        while self.sock.has_data():
            yield self.read()

def endpoint2socket(endpoint_url: typing.Union[Endpoint,str]) -> typing.Union[tcpsocket,serialsocket]:
    "Provides the appropriate *synchronous* socket for a given endpoint"
    endpoint = Endpoint(endpoint_url)
    if endpoint.scheme == "serial": # serial:/dev/ttyFooBar
        return serialsocket(endpoint.host)
    elif endpoint.scheme == "tcp": # tcp://192.168.1.2:5732
        return tcpsocket(endpoint.host, endpoint.port, auto_reconnect="auto_reconnect" in endpoint.args)
    elif endpoint.scheme in ["emu","sim"]: # emu:/ or emu:/?debug
        return emusocket(debug="debug" in endpoint.args)
    elif endpoint.scheme == "zeroconf":
        endpoint_url = detect(single=True)
        if not endpoint_url:
            raise ValueError("zeroconf:/ explicitely asked for, but no endpoint provided as argument or in ENV variable and could also not discover something on USB or in Network.")
        return endpoint2socket(endpoint_url)
    else:
        raise ValueError(f"Illegal {endpoint_url=}. Expecting something like tcp://192.168.1.2:5732 or serial:/dev/foo")


class Run:
    """
    A run is a IC-OP-HALT sequence on a LUCIDAC with measurement (data aquisition with the analog-digital-converters)
    ongoing during the OP phase. Therefore, a run generates data. This results in the remote site to send data "out of bounds",
    i.e. without that we have requested these data. The job of this class is to proper model how to receive these data.
    An instance of this class is returned by :meth:`LUCIDAC.start_run`. This instance is properly "handled off" by
    calling :meth:`data` and then wiping it.
    
    """
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
        while True:
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
                    break # successfully transfered all data
                if msg_new == "ERROR":
                    # TODO: This is actually a RemoteError,
                    #  but since we don't get a proper envelope but some weird extra message
                    #  which does not even hold a suitable error string, we have to come up
                    #  with something ourselves...
                    raise LocalError(f"Could not properly start the run. Most likely the DAQ ({self.hc.daq_config}) or RUN ({self.hc.run_config}) configuration not accepted by the server side.")
                # Attention: After runstate stop there still can come a last data
                #            package.
            else:
                raise LocalError(f"Run::slurp(): Unexpected message {envelope}")
                #return # stop slurping

    def data(self, empty_is_fine=False) -> typing.List[float]:
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
        
        :arg empty_is_fine: Whether to raise when no data have been aquired or
           happily return an empty array. Raising a ``LocalError`` (i.e. the default
           option) is most likely more what you want because you then don't have to
           write error handling code for an empty array. Otherwise a later access on
           something on  ``np.array(run.data())`` will most likely result in an
           ``IndexError: index 0 is out of bounds for axis 0 with size 0`` or similar.
        """
        res = sum(self.next_data(), []) # joins lists at outer level
        if len(res) == 0 and not empty_is_fine:
            raise LocalError("Expected data stream but got not a single data point")
        return res

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
        
        For details, see :ref:`lucipy-detection`.
    :param auto_reconnect: Whether reconnect in case of loss connection (TODO: Move
        to parameter ``?reconnect`` in the endpoint URL syntax)
    """
   
    ENDPOINT_ENV_NAME = "LUCIDAC_ENDPOINT"
    
    # a list of commands which will be exposed as methods, for shorthands.

    # TODO: Maybe write more verbose as in pyanalog in order to have a more usable documentation!
    commands = """
        ping help
        reset_circuit set_circuit get_circuit
        get_entities
        stop_run
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
    
    def __init__(self, endpoint_url=None, auto_reconnect=True):
        if not endpoint_url:
            if self.ENDPOINT_ENV_NAME in os.environ:
                endpoint_url = os.environ[self.ENDPOINT_ENV_NAME]
            else:
                endpoint_url = detect(single=True) 
                # should raise an ModuleNotFoundError if and only if a library is missing which could have found something
                if not endpoint_url:
                    raise ValueError("No endpoint provided as argument or in ENV variable "
                                     + self.ENDPOINT_ENV_NAME + 
                                     " and did not discover an USB or network endpoint. No missing external libraries encountered.")
                    # self.ENDPOINT_ENV_NAME is used instead of the hardcoded string in case
                    # one wants to modify the env variable name.

        endpoint = Endpoint(endpoint_url)
        socket = endpoint2socket(endpoint_url)
        self.sock = jsonlines(socket)
        self.req_id = 50
        
        #: Ethernet Mac address of Microcontroller, required for the circuit entity hierarchy
        self.hc_mac = None
        # TODO: Maybe change firmware once in a way that it doesn't really need the client to know it
        
        #: Storage for stateful preparation of runs.
        self.run_config = dotdict(
            halt_on_external_trigger = False,
            halt_on_overload  = True,
            ic_time = 123456, # ns 
            op_time = 234567, # ns
        )

        #: Storage for stateful preparation of runs.
        self.daq_config = dotdict(
            num_channels = 0,
            sample_op = True,
            sample_op_end = True,
            sample_rate = 500_000,
        )
        
        # remember credentials for later use
        self.user = endpoint.user
        self.password = endpoint.password
    
    def __repr__(self):
        return f"LUCIDAC(\"{self.sock.sock}\")"
    
    def close(self):
        """
        Closes connection to LUCIDAC. This will close the socket and should be used
        when destructing the object. In most scripts it should be not neccessary to call
        ``close`` explicitely becaue the connection is considered ephermal for the script
        runtime. However, in unit testing conditions it might be interesting to close a
        connection in order to be able to reuse the socket ports later.
        """
        return self.sock.close()
    
    def send(self, msg_type, msg={}):
        "Sets up an envelope and sends it, but does not wait for reply"
        envelope = dict(id=self.req_id, type=msg_type, msg=msg)
        self.req_id += 1
        self.sock.send(envelope)
        return envelope

    def _recv(self, sent_envelope, ignore_run_state_change=True):
        resp = dotdict(self.sock.read())
        if ignore_run_state_change and "type" in resp and resp.type == "run_state_change":
            log.info(f"run_state_change: {resp.msg}")
            return self._recv(sent_envelope, ignore_run_state_change=True)
        if sent_envelope == resp:
            # This is a serial socket replying first what was typed. Read another time.
            return self._recv(sent_envelope, ignore_run_state_change=ignore_run_state_change)
        if "error" in resp:
            raise RemoteError(resp)
        if resp.type == sent_envelope.type:
            # Do not show the empty message, in case of success.
            return resp.msg if resp.msg != {} else None
        else:
            log.error(f"req(type={sent_envelope.type}) received unexpected: {resp=}")
            return resp

    def query(self, msg_type , msg={}, ignore_run_state_change=True):
        "Sends a query and waits for the answer, returns that answer"
        envelope = dotdict(self.send(msg_type, msg))
        return self._recv(envelope)
    
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
    
    def set_circuit(self, carrier_config, **further_commands):
        """
        This sets a carrier level configuration. The :mod:`~lucipy.circuits` module and
        in particular the :func:`~lucipy.circuits.Circuit.generate` method can help to
        produce these configuration data structures.
        
        Typically a configuration looks a bit like ``{"/0": {"/U": [....], "/C":[....], ...}}``,
        i.e. the entities for a single cluster. There is only one cluster in LUCIDAC.
        
        .. note::
        
           This also determines the ideal IC time *if* that has not been set
           before (either manually or in a previous run).
        """
        outer_config = {
            "entity": [self.get_mac()], # str(cluster_index)], # was "0", NOT "/0"
            "config": carrier_config,
            **further_commands
        }
        #print(outer_config)

        if "/0" in carrier_config:
            cluster_config = carrier_config["/0"]
            if "/M0" in cluster_config and not "ic_time" in self.run_config:
                self.run_config.ic_time = self.determine_idal_ic_time_from_k0s(cluster_config["/M0"])
            
        if "adc_channels" in carrier_config:
            from .simulator import remove_trailing
            num_channels = len(remove_trailing(carrier_config["adc_channels"], None))
            self.set_daq(num_channels=num_channels)
                    
        return self.query("set_circuit", outer_config)
        
    
    def set_config(self, circuit):
        "set_config was renamed to set_circuit in later firmware versions"
        return self.set_circuit(circuit)
    
    def set_circuit_alt(self, circuit):
        # manually decompose /0
        carrier_config = circuit
        if "/0" in carrier_config:
            self.query("set_circuit", {
                "entity": [self.get_mac(), "0"],
                "config": carrier_config["/0"]
            })
            del carrier_config["/0"]
        self.set_circuit(carrier_config)
    
    @staticmethod
    def resolve_path(path, config={}):
        """
        Provides the notational sugar for :meth:`set_by_path`.
        
        The path must point to an entity and not to an element. 
        An entity corresponds to a class on the firmware side which can receive configuration
        "elements". The path can be provided as string, such as ``/0/C``
        or ``0/C`` or as array of strings such as ``["0", "C"]``.
        
        Since this client has no information about the entity structure and the element
        configuration, it cannot accept paths which also include elements, such as
        ``/0/M0/elements/0/ic`` for setting the first integrator value. However, as
        a "nicety" it allows to generate a nested directory structure by introducing
        a "double slash" notation, which is ``/0/M0//elements/0/ic``, or as array,
        ``["0", "M0", "", "elements", "0", "ic"]``. Internally, such a call is then
        translated to the path ``0/M0`` and the configuration dictionary is wrapped as
        ``{ "elements": {"0": {"ic": actual_config } } }``. This way, one can set
        actual elements very conveniently.

        >>> LUCIDAC.resolve_path("/0/M0")
        (['0', 'M0'], {})
        >>> LUCIDAC.resolve_path("foo/bar", "baz")
        (['foo', 'bar'], 'baz')
        >>> LUCIDAC.resolve_path("foo/bar//baz", "kaz")
        (['foo', 'bar'], {'baz': 'kaz'})
        >>> LUCIDAC.resolve_path("foo/bar//bax/bay/baz", {"bir":"bur"})
        (['foo', 'bar'], {'bax': {'bay': {'baz': {'bir': 'bur'}}}})
            
        In the following real world example, all notations are equvialent:
        
        >>> a = LUCIDAC.resolve_path(["0", "M0"], {"elements":{"0": {"ic":0.23, "k":100} } })
        >>> b = LUCIDAC.resolve_path("/0/M0",     {"elements":{"0": {"ic":0.23, "k":100} } })
        >>> c = LUCIDAC.resolve_path("/0/M0//elements/0",         {"ic":0.23, "k":100})
        >>> print(a)
        (['0', 'M0'], {'elements': {'0': {'ic': 0.23, 'k': 100}}})
        >>> assert a == b and b == c

        """
        if isinstance(path, str):
            apath = path.split("/")
            if apath[0] == "": # remove leading slash if it was there
                apath.pop(0)
            if apath.count("") == 1: # entity-element split given
                split_index = apath.index("")
                entity_path, element_path = apath[:split_index], apath[split_index+1:]
                wrapper_config = config
                for e in element_path[::-1]:
                    wrapper_config = { e: wrapper_config }
                return (entity_path, wrapper_config)
            elif apath.count("") > 1:
                raise ValueError(f"'{path}': Invalid entity path given. Entity-Element split '//' can only applied once.")
            path = apath
        return (path, config)
    
    def set_by_path(self, path, config):
        """
        Set element configuration by path.
        
        This is a fine-granular alternative to :meth:`set_circuit`. For the meaning of
        ``path``, see :meth:`resolve_path`.

        Note that the path is always relative to the carrier, not the cluster. That means
        most of the time you want to address the cluster just by ascending with the
        entity path "0".
         
        When providing entities as list, do not prepend entities with a slash, i.e. do
        not write ``[..., "/M0", ...]`` but just  ``[..., "M0", ...]``.
        Slash-prefixed entitiy names happen to take place only in the
        configuration dictionary (second parameter).
        
        All these following lines are equivalent formulations for the same aim:
        
        >>> hc = LUCIDAC("emu:/")
        >>> hc.set_by_path(["0", "M0"], {"elements":{0: {"ic":0.23, "k":100} } })
        >>> hc.set_by_path("/0/M0",     {"elements":{0: {"ic":0.23, "k":100} } })
        >>> hc.set_by_path("/0/M0//elements/0",         {"ic":0.23, "k":100})
        >>> hc.get_circuit()["config"]["/0"]["/M0"]["elements"]["0"]
        {'ic': 0.23, 'k': 100}

        """
        path, config = self.resolve_path(path, config)
        
        cluster_index = 0
        outer_config = {
            "entity": [self.get_mac()] + path, #[self.get_mac(), str(cluster_index)] + path,
            "config": config
        }
        return self.query("set_circuit", outer_config)
    
    def set_leds(self, leds_as_integer):
        # Cannot use set_circuit because it operates only on th Carrier
        return self.query("set_circuit", {"entity": [self.get_mac(), "FP" ], "config": { "leds": leds_as_integer } })
        
    def signal_generator(self, dac=None):
        """
        :args dac: Digital analog converter outputs, as there are two a list with two floats (normalized [-1,+1]) is expected
        """
        return self.query("set_circuit", {"entity": [self.get_mac(), "FP" ], "config": {
            "signal_generator":  { "dac_outputs": dac, "sleep": False }
        } })
    
    def set_op_time(self, *, ns=0, us=0, ms=0, sec=0, k0fast=0, k0slow=0):
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
        :param sec: seconds
        :param k0fast: units of k0fast, i.e. the fast integrators. Measuring time in
               this units means that within the time ``k0fast=1``` an integrator
               integrates a constant 1 from initial value 0 to final value 1.
        :param k0slow: units of k0slow. A slow integrators computes within time ``k0slow=1``
               a constant 1 from initial vlaue 0 to final value 1.

        """
        optime_ns  = ns + us*1e3 + ms*1e6 + sec*1e9
        optime_ns += k0fast*1e5 + k0slow*1e7
        self.run_config.op_time = int(optime_ns)
        return self.run_config.op_time
    
    #: Sample rates per second accepted by the system.
    allowed_sample_rates = [1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 80, 100, 125, 160, 200, 250, 320, 400, 500, 625, 800, 1000, 1250, 1600, 2000, 2500, 3125, 4000, 5000, 6250, 8000, 10000, 12500, 15625, 20000, 25000, 31250, 40000, 50000, 62500, 100000, 125000, 200000, 250000, 500000, 1000000]
    
    def set_daq(self, *,
            num_channels = None,
            sample_op = None,
            sample_op_end = None,
            sample_rate = None,
            ):
        """
        :param num_channels: Data aquisition specific - number of channels to sample. Between
           0 (no data aquisition) and 8 (all channels)
        :param sample_op: Sample a first point exactly when optime starts
        :param sample_op_end: Sample a last point exactly when optime ends
        :param sample_rate: Number of samples per second. Note that not all numbers are
           supported. A client side check is performed.
        """
        if num_channels != None:
            if not (0 <= num_channels and num_channels <= 8):
                raise ValueError("Require 0 <= num_channels <= 8")
            self.daq_config.num_channels = num_channels

        if sample_op != None: # boolean
            self.daq_config.sample_op = sample_op
        if sample_op_end != None: # boolean
            self.daq_config.sample_op_end = sample_op_end
        
        if sample_rate != None:
            if not sample_rate in self.allowed_sample_rates:
                raise ValueError(f"{sample_rate=} not allowed. Firmware supports only values from the following list: {self.allowed_sample_rates}")
            self.daq_config.sample_rate = sample_rate
       
        return self.daq_config

    def set_run(self, *,
            halt_on_external_trigger = None,
            halt_on_overload = None,
            ic_time = None,
            op_time = None,
            no_streaming = None,
            repetitive = None,
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
        if halt_on_external_trigger != None:
            self.run_config.halt_on_external_trigger = halt_on_external_trigger
        if halt_on_overload != None:
            self.run_config.halt_on_overload = halt_on_overload
        if ic_time != None:
            self.run_config.ic_time = ic_time
        if op_time != None:
            self.run_config.op_time = op_time
        if no_streaming != None:
            self.run_config.no_streaming = no_streaming
        if repetitive != None:
            self.repetitive = repetitive
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

for cmd in LUCIDAC.commands:
    shorthand = (lambda cmd: lambda self, msg={}: self.query(cmd, msg))(cmd)
    shorthand.__doc__ = f'Shorthand for ``query("{cmd}", msg)``, see :meth:`query`.'
    #shorthand = types.MethodType(shorthand, self) # bind function
    if hasattr(functools, "cache") and cmd in LUCIDAC.memoizable:
        shorthand = functools.cache(shorthand)
    if not hasattr(LUCIDAC, cmd):
        setattr(LUCIDAC, cmd, shorthand)

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
