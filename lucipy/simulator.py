import sys, socket, select, threading, socketserver, json, functools, operator # python internals

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
    A simulator for the LUCIDAC. Please :ref:`refer to the documentation <lucipy-sim>`
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
    
        """
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

class Emulation:
    """
    A super simple LUCIDAC emulator. This class allows to start up a TCP/IP server
    which speaks part of the JSONL protocol and emulates the same way a LUCIDAC teensy
    would behave.
    
    .. note::
        Since the overall code does not use asyncio as a philosophy, also this code is
        written as a very traditional forking server. In our low-volume practice, there
        should be no noticable performance penalty.
        
        Note that the forking nature of the server also implements a single state per client!
    """
    
    # "python" as Mac address "70-79-74-68-6f-6e" just for fun
    default_emulated_mac = "-".join("%x"%ord(c) for c in "python")

    def get_entities(self):
        "Just returns the standard LUCIDAC REV0 entities with the custom MAC address."
        return {
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
    
    def get_config(self):
        "Read out circuit configuration"
        return self.circuit
    
    def get_circuit(self):
        "Read out circuit configuration"
        return self.circuit
            
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
        
    def start_run(self, run_config, daq_config):
        # TODO: Emulate these state change messages
        t_final = run_config["op_time"]
        sim = simulation(self.circuit, realtime=True)
        data = sim.solve_ivp(t_final)
        # TODO need to directly write out these data messages, probably
        #      resample the data poins        
    
    def handle_request(self, line):
        "Handles incoming JSONL encoded envelope and respons with a string encoded JSONL envelope"
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
            
            if hasattr(self, envelope["type"]):
                method = getattr(self, envelope["type"])
                # This should be wrapped with a generic exception catcher passing any kind of errors
                # to the caller
                try:
                    if "msg" in envelope and isinstance(envelope["msg"], dict):
                        ret["msg"] = method(**envelope["msg"])
                    else:
                        ret["msg"] = method()
                except Exception as e:
                    print(f"Exception at handling {envelope=}: ", e)
                    ret["msg"] = {"error": f"During handling this message, an exception occured: {e}" }
            else:   
                ret["msg"] = {'error': "Don't know this message type"}
        except json.JSONDecodeError as e:
            ret = { "msg": { "error": f"Cannot read message '{line}', error: {e}" } }
            
        if isinstance(ret["msg"], dict) and "error" in ret["msg"]:
            ret["error"] = ret["msg"]
            ret["status"] = -2
        else:
            ret["status"] = 0
        
        return json.dumps(ret) + "\n"
    
    def __init__(self, bind_ip="127.0.0.1", bind_port=5732, emulated_mac=default_emulated_mac):
        self.mac = emulated_mac
        self.reset()
        parent = self
        
        class TCPRequestHandler(socketserver.StreamRequestHandler):
            #def setup(self):
             #   print(f"{self.client_address} connected")
                #print(f"{self.rfile=}, {self.wfile=}")
                #self.fh = self.request.makefile(mode="rw", encoding="utf-8")
            def handle(self):
                
                from .synchc import has_data
                
                #self.request.settimeout(2) # 2 seconds
                
                #try:
                    #self.wfile.write(b'{"type":"hans","this is to say hello":"yo"}\n')
                if 1:
                    print(f"Waiting for {self.client_address}")
                    print(f"{has_data(self.rfile)=} {has_data(self.wfile)=}")
                    line = self.rfile.readline().decode("utf-8")
                    print(f"Got {line=}")
                    response = parent.handle_request(line)
                    print(f"Writing out {response=}")
                    #self.request.sendall(response.encode("ascii"))
                    self.wfile.write(response.encode("utf-8"))
                    self.wfile.flush()
                #except (BrokenPipeError, KeyboardInterrupt) as e:
                #    print(e)
                #    return
            #def finish(self):
            #    print(f"{self.client_address} disconnected")
                
        #class TCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
        class TCPServer(socketserver.TCPServer):
            pass
        
        self.server = TCPServer((bind_ip, bind_port), TCPRequestHandler)
    
    def serve_forever(self):
        with self.server:
            print("Server running, stop with CTRL+C")
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                print("Keyboard interrupt")
                self.server.server_close()
                return
            except Exception as e:
                print(f"Server crash: {e}")
                return
            
            
        
