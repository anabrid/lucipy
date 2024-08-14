
# python internals
import sys, socket, select, threading, socketserver, json, functools, \
  operator, functools, time, datetime

# only for debugging; very helpful to display big matrices in one line

# np.set_printoptions(edgeitems=30, linewidth=1000, suppress=True)

def split(array, nrows, ncols):
    """
    Split a matrix into sub-matrices.
    Provides one new axis over the array (linearized).
    """
    r, h = array.shape
    return (array.reshape(h//nrows, nrows, -1, ncols)
                 .swapaxes(1, 2)
                 .reshape(-1, nrows, ncols))


class Simulation:
    """
    A simulator for the LUCIDAC. Please :ref:`refer to the documentation <sim>`
    for a theoretical and practical introduction.
    
    Important properties and limitations:
    
    * Currently only understands mblocks ``M1 = Mul`` and ``M0 = Int``
    * Unrolls Mul blocks at evaluation time, which is slow
    * Note that the system state is purely hold in I.
    * Note that k0 is implemented in a way that 1 time unit = 10_000 and
      k0 slow results are thus divided by 100 in time.
      Should probably be done in another way so the simulation time is seconds.
    
    :arg realtime: If set, resulting times will be in seconds. If not, k0=10.000
      equals time unit 1.
    """
    
    def __init__(self, circuit, realtime=False):
        import numpy as np

        UCI = circuit.to_dense_matrix()
        self.A, self.B, self.C, self.D = split(UCI, 8, 8)
        self.ics = circuit.ics
        
        # fast = 10_000, slow = 100
        global_factor = 1 if realtime else 10_000
        self.int_factor = np.array(circuit.k0s) / global_factor
        
    def Mul_out(self, Iout):
        "Determine Min from Iout, the 'loop unrolling' way"
        import numpy as np

        Min0 = np.zeros((8,)) # initial guess
        constants = np.ones((4,)) # constant sources on Mblock
        
        # Compute the actual MMulBlock, computing 4 multipliers and giving out constants.
        mult_sign = -1 # in LUCIDACs, multipliers negate!
        Mout_from = lambda Min: np.concatenate((mult_sign*np.prod(Min.reshape(4,2),axis=1), constants))
        
        Mout = Mout_from(Min0)
        Min = Min0
        
        max_numbers_of_loops = 4 # = number of available multipliers (in system=on MMul)
        for loops in range(max_numbers_of_loops+1):
            Min_old = Min.copy()
            Min = self.A.dot(Mout) + self.B.dot(Iout)
            Mout = Mout_from(Min)
            #print(f"{loops=} {Min=} {Mout=}")

            # this check is fine since exact equality (not np.close) is required.
            # Note that NaN != NaN, therefore another check follows
            if np.all(Min_old == Min):
                break
            
            if np.any(np.isnan(Min)) or np.any(np.isnan(Mout)):
                raise ValueError(f"At {loops=}, occured NaN in {Min=}; {Mout=}")

        else:
            raise ValueError("The circuit contains algebraic loops")
        
        #print(f"{loops=} {Mout[0:2]=}")
        return Mout
    
    def nonzero(self):
        """
        Returns the number of nonzero entries in each 2x2 block matrix. This makes it easy to
        count the different type of connections in a circuit (like INT->INT, MUL->INT, INT->MUL, MUL->MUL).
        """
        import numpy as np
        sys = np.array([[self.A,self.B],[self.C,self.D]])
        return np.sum(sys != 0, axis=(2,3))

    
    def rhs(self, t, state, clip=True):
        "Evaluates the Right Hand Side as in ``d/dt state=rhs(t,state)``"
        Iout = state
        
        #eps = 1e-2 * np.random.random()
        eps = 0.2
        if clip:
            Iout[Iout > +1.4] = +1.4 - eps
            Iout[Iout < -1.4] = -1.4 + eps

        Mout = self.Mul_out(Iout)
        Iin = self.C.dot(Mout) + self.D.dot(Iout)
        int_sign  = +1 # in LUCIDAC, integrators do not negate
        #print(f"{Iout[0:2]=} -> {Iin[0:2]=}")
        #print(t)
        return int_sign * Iin * self.int_factor
    
    def solve_ivp(self, t_final, clip=True, ics=None, **kwargs_for_solve_ivp):
        """
        Solves the initial value problem defined by the LUCIDAC Circuit.
        
        Good-to-know options for solve_ivp:
    
        :arg t_final: Final time to run simulation to. Start time is always 0. Units depend
           on ``realtime=True/False`` in constructor.
        :arg ics: Initial Conditions to start with. If none given, the MIntBlock configuration
           is used. If given, a list with ``0 <= size <= 8`` has to be provided.
        :arg clip: Whether to carry out bounded-in-bounded-out value clipping as a real analog computer would do
        :arg dense_output: value ``True``allows for interpolating on ``res.sol(linspace(...))``
        :arg method: value ``LSODA`` is good for stiff problems
        :arg t_eval: In order to get a solution on equidistant time, for instance you can
           pass this option an ``np.linspace(0, t_final, num=500)``
        
        Quick usage example:
        
        >>> e = Circuit()
        >>> ramp  = e.int(ic = -1)  # makes an Integrator
        >>> const = e.const()       # makes a  Constant giver
        >>> e.connect(const, ramp, weight = 0.1)
        >>> result = Simulation(e).solve_ivp(500)
        >>> ramp_result = result.y[0] # unpack the first integrator output
        >>> plt.plot(result.t, ramp_result) # plot against solution times
    
        """
        import numpy as np
        if np.all(ics == None):
            ics = self.ics
        elif len(ics) < len(self.ics):
            ics = list(ics) + [0]*(len(self.ics) - len(ics))
        
        from scipy.integrate import solve_ivp
        data = solve_ivp(lambda t,state: self.rhs(t,state,clip), [0, t_final], ics, **kwargs_for_solve_ivp)
        
        #assert data.status == 0, "ODE solver failed"
        #assert data.t[-1] == t_final
        
        return data


def find(element, structure):
    return functools.reduce(operator.getitem, element, structure)

def expose(f):
    f.exposed = True
    return f

class Emulation:
    """
    A super simple LUCIDAC emulator. This class allows to start up a TCP/IP server
    which speaks part of the JSONL protocol and emulates the same way a LUCIDAC teensy
    would behave. It thus is a shim layer ontop of the Simulation class which gets a
    configuration in and returns numpy data out. The Emulation instead will make sure it
    behaves as close as possible to a real LUCIDAC over TCP/IP.
        
    In good RPC fashion, methods are exposed via a tiny registry and marked ``@expose``.
    
    The emulation is very superficial. The focus is on getting the configuration in and
    some run data which allows for easy developing new clients, debugging, etc. without
    a real LUCIDAC involved.
        
    Please :ref:`refer to the documentation <emu>` for a high level introduction.
    
    .. note::
        Since the overall code does not use asyncio as a philosophy, also this code is
        written as a very traditional forking server. In our low-volume practice, there
        should be no noticable performance penalty.

    """
    
    default_emulated_mac = "-".join("%x"%ord(c) for c in "python")
    "The string 'python' encoded as Mac address 70-79-74-68-6f-6e just for fun"

    @expose
    def get_entities(self):
        "Just returns the standard LUCIDAC REV0 entities with the custom MAC address."
        return {'entities': {
            self.mac: {'/0': {'/M0': {'class': 2,
                'type': 0,
                'variant': 0,
                'version': 0},
            '/M1': {'class': 2, 'type': 1, 'variant': 0, 'version': 0},
            '/U': {'class': 3, 'type': 0, 'variant': 0, 'version': 0},
            '/C': {'class': 4, 'type': 0, 'variant': 0, 'version': 0},
            '/I': {'class': 5, 'type': 0, 'variant': 0, 'version': 0},
            'class': 1,
            'type': 3,
            'variant': 0,
            'version': 0},
            'class': 0,
            'type': 0,
            'variant': 0,
            'version': 0}}
        }

    def micros(self):
        "Returns microseconds since initialization, mimics microcontroller uptime"
        uptime_sec = self.started - time.time()
        return int(uptime_sec / 1e6)

    @expose
    def ping(self):
        return { "now": datetime.now().isoformat(), "micros": self.micros() }
        
    @expose
    def reset(self):
        "Resets the circuit configuration"
        self.circuit = {'entity': None,
            'config': {'/0': {
                '/M0': {'elements': [ {'ic': 0, 'k': 10000} for i in range(8) ], },
                '/M1': {},
                '/U': {'outputs': [ None for i in range (32) ] },
                '/C': {'elements': [ 0 for i in range(32) ] },
                '/I': {'outputs': [ None for i in range(16) ] }
                }
            }
        }
    
    @expose
    def get_config(self):
        "Read out circuit configuration"
        return self.circuit
    
    @expose
    def get_circuit(self):
        "Read out circuit configuration"
        return self.circuit
    
    @expose
    def set_config(self, config):
        "Set circuit configuration"
        # well, now we should have to parse that config message,
        # patch the circuit structure and everything. What a mess!
        enity, new_config = config["entitiy"], config["config"]
        print(f"set_config({config=})")
        # must deal with key not found etc errors
        target_circuit = find(entity, self.circuit)
        print(f"found {target_circuit=} replacing it now with {new_config=}")
        
        # the replacement structure...
        parent = find(entity[:-1], self.circuit)
        child_key = entity[-1]
        
        # TODO, test this
    
    #@expose("out-of-band")
    @expose
    def start_run(self, start_run_msg):
        """
        Emulate an actual run with the LUCIDAC Run queue and FlexIO data aquisition.
        
        This function does it all in one rush "in sync" , no need for a dedicated queue.
        
        Should react on a message such as the following:
        
        ::
        
            example_start_run_message = {
            'id': '417ebb51-40b4-4afe-81ce-277bb9d162eb',
            'session': None,
            'config': {
                'halt_on_external_trigger': False, # will ignore
                'halt_on_overload': True,          # 
                'ic_time': 123456,                 # will ignore
                'op_time': 234567                  # most important, determines simulation time
            },
            'daq_config': {
                'num_channels': 0,                 # should obey
                'sample_op': True,                 # will ignore
                'sample_op_end': True,             # will ignore
                'sample_rate': 500000              # will ignore
            }}
        
        Considering the DAQ, it will just return the nodal integration points for the
        time being. One *could* easily interpolate at the actual times, thought!
        
        """

        run_id = start_run_msg["id"]
        t_final = start_run_msg["config"]["op_time"]
        
        reply_envelopes = []
        reply_envelopes.append({
            "type": "run_state_change", "msg": { "id": run_id, "t": self.micros(), "old": "NEW", "new": "DONE" }
        })
        
        sim = simulation(self.circuit, realtime=True)
        data = sim.solve_ivp(t_final)
        
        # TODO need to directly write out these data messages, probably
        #      resample the data poins
        
    
    @expose
    def help(self):
        return {
            "human_readable_info": "This is the lucipy emulator",
            "available_types": list(self.exposed_methods().keys())
        }
    
    def exposed_methods(self):
        "Returns a dictionary of exposed methods with string key names and callables as values"
        all_methods = (a for a in dir(self) if callable(getattr(self, a)) and not a.startswith('__'))
        exposed_methods = { a: getattr(self, a) for a in all_methods if hasattr(getattr(self, a), 'exposed') }
        return exposed_methods
    
    
    def handle_request(self, line, writer=None):
        """
        Handles incoming JSONL encoded envelope and respons with a string encoded JSONL envelope
    
        :param line: String encoded JSONL input envelope
        :param writer: Callback accepting a single binary string argument. If provided, is used
            for firing out-of-band messages during the reply from a handler. Given the linear
            program flow, it shall be guaranteed that the callback is not called after return.
        :returns: String encoded JSONL envelope output
        """
        
        # decided halfway to do it in another way
        #json_writer = (lambda envelope: writer((json.dumps(envelope)+"\n").encode("utf-8"))) if writer else None
        
        def decorate_protocol_reply(ret):
            if isinstance(ret["msg"], dict) and "error" in ret["msg"]:
                ret["error"] = ret["msg"]["error"]
                ret["msg"] = {}
                ret["status"] = -2
            else:
                ret["status"] = 0
            
            return json.dumps(ret) + "\n"
        
        try:
            if not line or line.isspace():
                return "\n"
            envelope = json.loads(line)
            print(f"Parsed {envelope=}")
            ret = {}
            if "id" in envelope:
                ret["id"] = envelope["id"]
            if "type" in envelope:
                ret["type"] = envelope["type"]
            
            methods = self.exposed_methods()
            if envelope["type"] in methods:
                method = methods[ envelope["type"] ]
                try:
                    msg_in = envelope["msg"] if "msg" in envelope and isinstance(envelope["msg"], dict) else {}

                    #if method.exposed == "out-of-band":
                        #ret["msg"] = method(**msg_in, writer=json_writer)
                    #else:
                    
                    # The outcome is EITHER just a single msg_out
                    # OR it is a list of whole RecvEnvelopes
                
                    outcome = method(**msg_in)
                    
                    if isinstance(outcome, list):
                        return list(map(decorate_protocol_reply, outcome))
                    else:
                        ret["msg"] = outcome
                except Exception as e:
                    print(f"Exception at handling {envelope=}: ", e)
                    ret["msg"] = {"error": f"During handling this message, an exception occured: {e}" }
            else:   
                ret["msg"] = {'error': "Don't know this message type"}
        except json.JSONDecodeError as e:
            ret = { "msg": { "error": f"Cannot read message '{line}', error: {e}" } }
            
        return decorate_protocol_reply(ret)
    
    def __init__(self, bind_addr="127.0.0.1", bind_port=5732, emulated_mac=default_emulated_mac):
        """
        :arg bind_addr: Adress to bind to, can also be a hostname. Use "0.0.0.0" to listen on all interfaces.
        :art bind_port: TCP port to bind to
        """
        self.mac = emulated_mac
        self.reset()
        self.started = time.time()
        parent = self
        
        class TCPRequestHandler(socketserver.StreamRequestHandler):
            def handle(self):
                print(f"New Connection from {self.client_address}")
                #from .synchc import has_data
                #self.request.settimeout(2) # 2 seconds
                while True:
                    try:
                        #print(f"{has_data(self.rfile)=} {has_data(self.wfile)=}")
                        line = self.rfile.readline().decode("utf-8")
                        #print(f"Got {line=}")
                        response = parent.handle_request(line, writer=self.wfile.write)
                        #print(f"Writing out {response=}")
                        #self.request.sendall(response.encode("ascii"))
                        
                        # allow multiple responses
                        responses = [response] if not isinstance(response, list) else response
                        
                        for res in responses:
                            self.wfile.write(res.encode("utf-8"))
                            
                        self.wfile.flush()
                    except (BrokenPipeError, KeyboardInterrupt) as e:
                        print(e)
                        return
        
        self.addr = (bind_addr, bind_port)
        self.handler_class = TCPRequestHandler
    
    def serve_forever(self, forking=False):
        """
        Hand over control to the socket server event queue.
    
        .. note::
            If you choose a forking server, the server can handle multiple clients a time
            and is not "blocking" (the same way as the early real firmware embedded servers were).
            However, the "parallel server" in a forking (=multiprocessing) model also means
            that each client gets its own virtualized LUCIDAC due to the multiprocess nature (no
            shared address space and thus no shared LUCIDAC memory model) of the server.
    
        :param forking: Choose a forking server model
        """
        
        if forking:
            class TCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
                pass
        else:
            class TCPServer(socketserver.TCPServer):
                pass
            
        self.server = TCPServer(self.addr, self.handler_class)
        
        with self.server:
            print(f"Lucipy LUCIDAC Mockup Server listening at {self.addr}, stop with CTRL+C")
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                print("Keyboard interrupt")
                self.server.server_close()
                return
            except Exception as e:
                print(f"Server crash: {e}")
                return
            
            
        
