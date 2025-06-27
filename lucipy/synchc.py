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
    itertools, os, functools, collections, uuid, time, warnings
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
            print(f"tcpsocket.read(): {e}. Input Bytes are: {e.object}")
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
        print(f"serialsocket.send({sth})")
        self.fh.write(sth.encode("ascii") + b"\n")
        self.fh.flush()
        print(f"serialsocket.send completed")
    def read(self):
        # block until have read exactly one line
        while self.has_data():
            ret = self.fh.readline()
            print(f"serialsocket.read(): {ret}")
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
    def __init__(self, actual_socket, ignore_invalid_json_reads=False):
        self.sock = actual_socket
        self.ignore_invalid_json_reads = ignore_invalid_json_reads
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
        #print("jsonlines.read() got ", read)
        while not read or not read.strip():
            print("haven't read anything, trying again")
            time.sleep(0.2)
            read = self.sock.read(*args, **kwargs)
        #print(f"jsonlines.read() got {read}")
        try:
            return json.loads(read)
        except json.JSONDecodeError as s:
            if self.ignore_invalid_json_reads:
                log.info(f"Received non-JSON message: '{read}'. Will read again")
                return self.read(*args, **kwargs)
            else:
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

        # in newer versions of the firmware, when `sample_op_end` is set in the
        # run_config, the state of all M-elements is sent - when reading messages,
        # we store this data separately from the data during the run
        self.op_end_data = None
    
    def next_data(self, mark_op_end_by_none: bool = False) -> typing.Optional[typing.Iterator[typing.List[float]]]:
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

        :arg mark_op_end_by_none: For repetitive runs, if set, return a "None" entry
            everytime an IC/OP cycle ended.
        """
        while True:
            envelope = self.hc.sock.read()
            if envelope["type"] == "run_data":
                # TODO check for proper run id and entity.

                if "state" in envelope["msg"] and envelope["msg"]["state"] == "OP_END":
                    if self.op_end_data is None:
                        self.op_end_data = []
                    self.op_end_data.append(envelope["msg"]["data"])
                    continue

                msg_data = envelope["msg"]["data"]
                assert all(self.hc.daq_config["num_channels"] == len(line) for line in msg_data)
                yield msg_data
            elif envelope["type"] == "run_state_change":
                msg_old = envelope["msg"]["new"]
                msg_new = envelope["msg"]["new"]
                if msg_new == "DONE":
                    if self.hc.run_config.repetitive:
                        if mark_op_end_by_none:
                            yield None
                    else:
                        break # computation was stopped or or circuit run was done
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
    
    def op_end_state(self) -> typing.Optional[typing.List[typing.List[float]]]:
        """
        When `sample_op_end` in the run config is `True`, the device will 
        return the M-block's satte, i.e. its outputs at the end of the OP-cycle.

        :return M-outputs at the end of the OP_cycle.
        """
        return self.op_end_data
    
    def stop(self) -> bool:
        """
        Stops a current run. This is meant for repetitive runs.

        :return True if the computation was stopped, False if there was an error.
        """

        # while the run is active, other messages could be sent in between this
        # query and the `stop_run` answer, hence don't assume that the next message
        # is the confirmation
        self.hc.query("stop_run", {
            "end_repetitive": True
        },
        ignore_response = True)

        # reads remaining messages until a `stop_run` confirmation is sent
        while True:
            envelope = self.hc.sock.read()

            if envelope['type'] == "stop_run":
                return (envelope["code"] == 0)
            else:
                # ignore other enevlopes for now
                pass

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
    ## TODO: Get rid of this memoization because with arguments it can lead to weird errors, for instance
    #    hc.sys_ident(dict(blink=True))  -> TypeError: unhashable type: 'dict'
    
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
        self.sock = jsonlines(socket, ignore_invalid_json_reads = endpoint.scheme == "serial")
        self.req_id = 50
        
        #: Ethernet Mac address of Microcontroller, required for the circuit entity hierarchy
        self.hc_mac = None
        
        #: Storage for stateful preparation of runs.
        self.run_config = dotdict(
            halt_on_external_trigger = False,
            halt_on_overload  = True,
            
            # default way of specifying the ic_time/op_time in nanoseconds
            ic_time = 0,
            op_time = 0,
            
            # repetitive or unlimited runs
            unlimited_op_time = False,
            repetitive = False
        )

        #: Storage for stateful preparation of runs.
        self.daq_config = dotdict(
            num_channels = 0,
            sample_op = True,
            sample_op_end = True,
            sample_rate = 500_000,
        )
        
        #: Storage for additional configuration options which go next to each set_circuit call
        # Note: this causes issues with the current mainline firmware, so it is not send for now
        self.circuit_options = dotdict(
            # -> should all be moved into the firmware!
            reset_before=True,
            sh_kludge=True,
            mul_calib_kludge=True,
            calibrate_mblock=True,
            calibrate_offset=True,
            calibrate_routes=True,
        )
        
        self.user = endpoint.user
        self.password = endpoint.password
        
        if self.user:
            self.login()
    
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
        #self.req_id += 1
        self.req_id = str(uuid.uuid4())
        envelope = dict(id=self.req_id, type=msg_type, msg=msg)
        self.sock.send(envelope)
        return envelope
    
    def _recv(self, sent_envelope, ignore_run_state_change=True):
        resp = dotdict(self.sock.read())
        if ignore_run_state_change and "type" in resp and resp.type == "run_state_change":
            log.info(f"run_state_change: {resp.msg}")
            return self._recv(sent_envelope, ignore_run_state_change=True)
        if "type" in resp and resp.type == "log":
            log.info(f"Device Log {resp}")#[{resp.time}] {resp.msg}")
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

    def query(self, msg_type , msg={}, ignore_run_state_change=True, ignore_response=False):
        "Sends a query and waits for the answer, returns that answer"
        envelope = dotdict(self.send(msg_type, msg))

        if not ignore_response:
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
    
    def login(self, user=None, password=None):
        """
        Login to the system. If no credentials are given, falls back to the one from the
        endpoint URL.
        """
        if user == None:
            user = self.user
        if password == None:
            password = self.password
        if not user:
            raise ClientError(f"Cannot login because no user name was given. Endpoint is {this.endpoint}")
        # won't check on empty password despite it also is basically an error
        return self.query("login", dict(user=user, password=password))
        
    
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
        if mac[0] == "/": # if entity begins like "/04-E9-E5", wipe "/"
            mac = mac[1:]        
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
    
    def set_circuit(self,
            carrier_config,
            **further_commands):
        """
        This sets a carrier level configuration. The :mod:`~lucipy.circuits` module and
        in particular the :func:`~lucipy.circuits.Circuit.generate` method can help to
        produce these configuration data structures.
        
        Typically a configuration looks a bit like ``{"/0": {"/U": [....], "/C":[....], ...}}``,
        i.e. the entities for a single cluster. There is only one cluster in LUCIDAC.
        
        :param reset_before: Reset circuit configuration on device before setting the new one.
           Pass ``False`` for incrementally updating the configuration.
        :param sh_kludge: Make a SH Track-Inject cycle (after potential reset) before applying
           the configuration on the LUCIDAC.
        :param calibrate_...: Perform the device calibration scheme. Currently disabled.
        
        .. note::
        
           This also determines the ideal IC time *if* that has not been set
           before (either manually or in a previous run).
        """
        
        from .circuits import Circuit
        if isinstance(carrier_config, Circuit): # or Routing or ...
            carrier_config = carrier_config.generate()
        
        outer_config = dict(
            entity = [self.get_mac()], # str(cluster_index)], # was "0", NOT "/0"
            config =  carrier_config
        )
        
        # note: with the current mainline firmware, sending these options results
        # in incorrent results - thus, we skip this for now
        # outer_config = {**outer_config, **self.circuit_options}

        outer_config = {**outer_config, **further_commands}

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
        ...
        >>> hc.set_by_path("/0/M0",     {"elements":{0: {"ic":0.23, "k":100} } })
        ...
        >>> hc.set_by_path("/0/M0//elements/0",         {"ic":0.23, "k":100})
        ...
        >>> hc.get_circuit()["config"]["/0"]["/M0"]["elements"]["0"]
        {'ic': 0.23, 'k': 100}

        """
        path, config = self.resolve_path(path, config)
        
        cluster_index = 0
        outer_config = {
            "entity": [self.get_mac()] + path, #[self.get_mac(), str(cluster_index)] + path,
            "config": config,
            **self.circuit_options
        }
        return self.query("set_circuit", outer_config)
    
    def set_leds(self, leds_as_integer):
        return self.set_by_path("FP", { "leds": leds_as_integer })
        
    def signal_generator(self, dac=None):
        """
        :args dac: Digital analog converter outputs, as there are two a list with two floats (normalized [-1,+1]) is expected
        """
        return self.set_by_path("FP", {
            "signal_generator":  { "dac_outputs": dac, "sleep": False }
        })
    
    def set_op_time(self, *, ns=0, us=0, ms=0, sec=0, k0fast=0, k0slow=0, unlimited=False):
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
        :param unlimted: Infinite OP-Time (will only stop once being send the ``stop_run`` command)

        """
        optime_ns  = ns + us*1e3 + ms*1e6 + sec*1e9
        optime_ns += k0fast*1e5 + k0slow*1e7
        self.run_config.op_time = int(optime_ns)
        self.run_config.unlimited_op_time = unlimited
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
            unlimited_op_time = None,
            streaming = None,
            repetitive = None,
            ):
        """
        Set basic configuration for any upcoming run. This will be the baseline for any run-specific
        configuration. See also :meth:`set_op_time` for a more practical way of setting the op_time.
        See also :meth:`start_run` for actually starting a run.
        
        :param halt_on_external_trigger: Whether halt the run if external input triggers
        :param halt_on_overload: Whether halt the run if overload occurs during computation
        :param ic_time: Request time to load initial conditions, in nanoseconds.
           This time depends on the k0 factors. However, it is rarely neccessary to tune this
           parameter, once useful values have been used. If not set, a value derived from the
           (first time in object lifetime) configuration set will be used.
        :param op_time: Request time for simulation, in nanoseconds. This is the most important
           option for this method. Note that by a current limitation in the hardware, only
           op_times < 1sec are supported.
        :param streaming Runs FlexIO code (currently always activated).
        :param repetitive: Loops between IC and OP mode until the user sends the stop_run command.
        """
        if halt_on_external_trigger != None:
            self.run_config.halt_on_external_trigger = halt_on_external_trigger
        if halt_on_overload != None:
            self.run_config.halt_on_overload = halt_on_overload
        if ic_time != None:
            self.run_config.ic_time = ic_time
        if op_time != None:
            self.run_config.op_time = op_time
        if unlimited_op_time != None:
            self.run_config.unlimited_op_time = unlimited_op_time
        if streaming != None:
            self.run_config.streaming = streaming
            warnings.warn("Streaming parameter is currently ignored by the firmware.")
        if repetitive != None:
            self.run_config.repetitive = repetitive
        return self.run_config

    def start_run(self, clear_queue=True, end_repetitive=True, run_type="sleepy", **run_and_daq_config) -> Run:
        """
        Start a run on the LUCIDAC. A run is a IC/OP cycle. See :class:`Run` for details.
        In order to configurer the run, use :meth:`set_run` and :meth:`set_daq` before
        calling this method.
       
        :returns: a Run object which allows to read in the DAQ data.
        :param clear_queue: Clear queue before submitting, making sure any leftover
           repetitive run is wiped. This is equivalent to calling :meth:`stop_run` before
            this method.
        """
        
        for k,v in run_and_daq_config.items():
            if k in self.run_config:
                self.run_config[k] = v
            elif k in self.daq_config:
                self.daq_config[k] = v
            elif k == "op_time_unlimited": # another fix
                self.run_config["unlimited_op_time"] = v
            else:
                raise KeyError(f"Unknown configuration key '{k}'. Please manually assign to run_config, daq_config or elsewhere.")

        start_run_msg = dotdict(
            id = str(uuid.uuid4()),
            session = None,
            config = self.run_config,
            daq_config = self.daq_config,
            clear_queue = clear_queue,
            end_repetitive = end_repetitive,
            run_type = run_type,
        )
      
        # this is a hot-fix for being able to run guidebook examples with
        # old v1.0.0 firmware. Should be removed in the near future (end of 2024)
        if start_run_msg.config.unlimited_op_time == True and not "skip_unlimited_optime_kludge" in start_run_msg.config:
            if start_run_msg.daq_config.num_channels != 0:
                print("LUCIDAC.start_run: Mocking client-side unlimited run, will not acquire data.")
            self.manual_mode("ic")
            from time import sleep
            sleep(0.5)
            self.manual_mode("op")
            return None
        
        self.slurp() # slurp old run data or similar
        ret = self.query("start_run", start_run_msg)
        if ret:
            raise LocalError(f"Run did not start successfully. Expected answer to 'start_run' but got {ret=}")
    
        return Run(self)
    
    def run(self, **kwargs) -> Run:
        "Alias for :meth:`start_run`. See there for details."
        return self.start_run(**kwargs)
    
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
