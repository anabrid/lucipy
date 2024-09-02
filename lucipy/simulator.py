# python internals
import sys, os, socket, select, threading, socketserver, json, functools, \
  operator, functools, time, datetime, copy, threading, multiprocessing

"""
This package provides a simple Simulator for LUCIDAC which tries to align
the LUCIDAC configuration (UCI matrix) as close as possible to the canonical
formulation of a linear ODE problem. Since the LUCIDAC has the nonlinear
multiplier elements, "loop unrolling" is performed at evaluation time.
For a theoretical description, see the documentation :ref:`sim`.

Furthermore, the package also provides a simple Emulator which exposes a
network service that emulates how LUCIDAC reacts to commands. This allows
high level testing and evventualy swapping software against real hardware.

The package requires numpy/scipy.
"""

def split(array, nrows, ncols):
    """
    Split a matrix into sub-matrices.
    Provides one new axis over the array (linearized).
    """
    r, h = array.shape
    return (array.reshape(h//nrows, nrows, -1, ncols)
                 .swapaxes(1, 2)
                 .reshape(-1, nrows, ncols))

def remove_trailing(l, remove_value=None):
    i = len(l)
    while i > 0 and l[i - 1] == remove_value:
        i -= 1
    return l[:i]


class Simulation:
    """
    A simulator for the LUCIDAC. Please :ref:`refer to the documentation <sim>`
    for a theoretical and practical introduction.
    
    The Simulator has an API which is suitable for getting a LUCIDAC circuit solved in
    Python as easy as possible. The usage can boil down to something like
    ``integrator_data = Simulation(circuit).solve_ivp(t_final)``. In particular, the
    Simulator will allow to inspect the LUCIDAC and its internal states as much as you
    want.
    
    If you want to use an API which is simliar to the LUCIDAC Hybrid Controller, use the
    :class:`Emulation` instead. It uses the :class:`Simulation` under the head but does
    not expose it but instead just returns the requested ADC sampling values when using
    it in a way like
    ``e = Emulation(); e.set_circuit(circuit.generate()); data = e.start_run(...)``.
    This way, you can steer for instance the sampling times.
    In contrast, if not requested explicitely with suitable ADC settings, it won't
    return the full integrator state and also won't provide any support for ACL_IN/OUT
    or further device inspection, given the limited JSON_API of the LUCIDAC. See there
    for getting a list of limitations.
    
    Important properties and limitations:
    
    * Currently only understands mblocks ``M0 = Int`` and ``M1 = Mul`` in REV1-Hardware fashion
    * Unrolls Mul blocks at evaluation time, which is slow
    * Note that the system state is purely hold in the integrators.
      It always evolves all 8 integrators and returns all 8 integrators.
      It is up to the user to use the provided mapping functions to derive the
      neccessary output.
    * Note that by default ``k0`` is implemented in a way that ``1 time unit = 10_000``
      and ``k0`` slow results are thus divided by ``100`` in time. Use ``realtime``
      to measure simulation time in seconds instead.
    
    :arg circuit: An :class:`circuits.Circuit` object. We basically only need it
      in order to make use of the :meth:`~circuits.Circuit.to_dense_matrix` call.
    :arg realtime: If set, the simulation time unit will be ``1sec``. If not,
      ``k0=10.000`` equals time unit 1. That means, in this case time is measured
      in multiples of ``10us``. Such a time unit can be more natural for
      applications. You can set the time factor later by overwriting the ``int_factor``
      property.
    
   
    Note, here is a tip to display the big matrices in one line:
    
       >>> import numpy as np
       >>> np.set_printoptions(edgeitems=30, linewidth=1000, suppress=True)

    """
    
    def __init__(self, circuit, realtime=False):
        import numpy as np
        
        circuit.sanity_check()

        self.ics = np.array(circuit.ics)
        
        # C*U: only required for acl_out_values()
        U, C, I = circuit.to_dense_matrices()
        self.CU = C.dot(U)
        self.I = I
        assert self.CU.shape == (32,16)
        
        self.circuit = circuit # only used in set_acl_in
        self.use_acl_in = False # TODO unfinished work
        
        # whether to use the constant giver. If not 0/None, this 
        # also holds the magnitude/value of the constant (+-1, +-0.1)
        self.u_constant = circuit.u_constant
        
        if self.u_constant:
            # Handle the effects of the constant giver.
        
            #
            # | clanes | U lanes[0:16] | U lanes [16:32]
            # | ------ | ------        | -----     
            # | 14     |  Mblock out   | CONSTANTS
            # | 15     |  CONSTANTS    | Mblock out
            
            # items in Ublock where the Mblock out is masked
            # and instead the CONSTANTs fed in.
            where_u_masks_for_const = [ U[0:16, 15], U[16:32, 14] ]
            
            # compute how constants are connected in the system.
            # The constant vector has size 16 and adds up to the Mblocks_input
            ublock_const_output = np.hstack(where_u_masks_for_const)
            self.constant = I.dot(C.dot(ublock_const_output * self.u_constant))
            
            # cut out the relevant lines in system, no transmission possible from Mout to Min.
            for item in where_u_masks_for_const:
                item[:] = 0
            
            self.UCI = I.dot(C.dot(U))
        else:
            self.UCI = circuit.to_dense_matrix()
            self.constant = np.zeros((16,))
            
        self.A, self.B, self.C, self.D = split(self.UCI, 8, 8)            
        
        config = circuit.generate()
        self.acl_select = config["acl_select"] if "acl_select" in config else []
        self.adc_channels = config["adc_channels"] if "adc_channels" in config else []
        
        # fast = 10_000, slow = 100
        global_factor = 1 if realtime else 10_000
        self.int_factor = np.array(circuit.k0s) / global_factor
        
    def Mul_out(self, Iout, t=0):
        """
        Determine Min from Iout, the 'loop unrolling' way.
    
        :arg Iout: Output of MathInt-Block. This is a list with 8 floats. This
           is also the current system state.
        :arg t: Simulation time, as in :meth:`rhs`. Is *only* needed to be passed
           to the ``acl_in`` callback.
        :return: Mout, the output of the MathMul-Block. Numpy array of shape ``(8,)``
        """
        import numpy as np

        Min0 = np.zeros((8,)) # initial guess
        identities = Min0[0:4] # constant sources on MMulblock. TODO check if this is correct
        
        # Compute the actual MMulBlock, computing 4 multipliers and giving out constants.
        mult_sign = +1 # in LUCIDACs REV1, multipliers do *no more* negate!
        Mout_from = lambda Min: np.concatenate((mult_sign*np.prod(Min.reshape(4,2),axis=1), identities))
        
        Mout = Mout_from(Min0)
        Min = Min0
        
        max_numbers_of_loops = 4 # = number of available multipliers (in system=on MMul)
        for loops in range(max_numbers_of_loops+1):
            Min_old = Min.copy()
            
            # TODO: The choice of C and D is determined by the assumption of MMulBlock at M1 slot.
            Min = self.C.dot(Iout)
            if self.use_acl_in:
                # TODO: For REV1, the position of MMul and MInt changes anyway!
                #       This needs adoption.
                # The following lines are therefore not tested
                Mblocks = self.mblocks_output(Iout, Mout)
                CU_out = self.CU.dot(Mblocks)
                acl_in = self.acl_in_callback(self, t, Iout)
                CU_out[ range(24,32) ] = acl_in
                Mblocks_in = self.I.dot(CU_out)
                Min += Mblocks_in[0:8] # to be fixed for REV1
            else:
                Min += self.D.dot(Mout)
            Min += self.constant[8:16] # constants for M1
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
        count the different type of connections in a circuit (like ``INT->INT, MUL->INT, INT->MUL, MUL->MUL``).
        """
        import numpy as np
        sys = np.array([[self.A,self.B],[self.C,self.D]])
        return np.sum(sys != 0, axis=(2,3))

    
    def rhs(self, t, state, clip=False):
        "Evaluates the Right Hand Side (rhs) as in ``d/dt state=rhs(t,state)``"
        Iout = state
        
        #eps = 1e-2 * np.random.random()
        eps = 0.2
        if clip:
            Iout[Iout > +1.4] = +1.4 - eps
            Iout[Iout < -1.4] = -1.4 + eps

        Mout = self.Mul_out(Iout, t)
        
        # TODO: The choice of A and B is determined by MIntBlock at M0 position
        Iin = self.A.dot(Iout)
        if self.use_acl_in:
            # same restricts as in Mul_out!
            pass
        else:
            Iin += self.B.dot(Mout)
        Iin += self.constant[0:8] # constants for M0
        int_sign  = -1 # in LUCIDAC REV1, integrators *do* negate
        #print(f"{Iout[0:2]=} -> {Iin[0:2]=}")
        #print(t)
        return int_sign * Iin * self.int_factor
    
    def mblocks_output(self, Iout, Mout=None):
        """
        Returns the full two-Math block outputs as continous array, with indices from
        0 to 16.

        Current limitation (as in the overall Simulation): M0 and M1 positions are hardcoded.

        :arg Iout: The system state, i.e. the integrators as in the :meth:`rhs`
        :arg Mout: The output of the MMul-block. If not given, it is derived
             from the system state.
        """
        import numpy as np
        Iout = np.array(Iout)
        if Mout is None:
            Mout = np.array(self.Mul_out(Iout))
        Mblocks_output = np.hstack((Iout,Mout)) # TODO: Pay attention to M0 and M1
        return Mblocks_output
    
    def adc_values(self, state, adc_channels=None):
        """
        Return the adc values for a given rhs state and requested ADC channels.
        
        :arg state: The system state, i.e. the integrators as in the :meth:`rhs`
        :arg adc_channels: The ADC matrix configuration, i.e. the crosslanes which
          shall be mapped onto the ADC channels. If none is given, the one from
          the configuration is used. If the configuration has no ADC channels
          given, an exception is raised.
        """
        if adc_channels is None:
            if len(self.adc_channels) != 0:
                adc_channels = self.adc_channels
            else:
                raise ValueError("Must provide adc_channels, since the provided circuit defines none.")
        adc_channels = remove_trailing(adc_channels, None)
        return self.mblocks_output(state)[adc_channels]
    
    def acl_out_values(self, state):
        """
        Returns the ACL out values (i.e. the front panel outputs of LUCIDAC) for
        a given system state. The function always returns the full 8 ACL lanes,
        i.e. a numpy array with shape ``(8,)``, i.e. a list of size 8.
        
        Note that ACL_OUT is always connected in LUCIDAC and acts independently
        of ACL_IN.
        That means you can probe ACL_OUT without having to replace this signal
        with the equivalent ACL_IN circuit.
        """
        Mblock_output = self.mblocks_output(state)
        Cblock_output = self.CU.dot(Mblock_output)
        acl_lanes = range(24, 32)
        return Cblock_output[acl_lanes]
       
    def set_acl_in(self, callback=None):
        """
        Feed in external signals into the simulator by feeding via the Frontpanel.
        
        This function expects *callback* to be a function with signature
        ``up_to_eight_acl_in_values = callback(simulation_instance, t, state)``,
        i.e. a similar shape as the :meth:`rhs`. This way, you have full control
        wether you restrict yourself to a real LUCIDAC ACL_IN/OUT by only accessing
        :meth:`acl_out_values` or by doing something a real LUCIDAC cannot do,
        exploiting the overall inner states.
        
        If you want to remove the ACL_IN callback function, call the method with
        argument ``None``.
        
        .. warning::
        
           This is merely a stub, the ACL Input is NOT YET fully implemented.
        """
        self.use_acl_in = True
        self.acl_in_callback = callback

    def solve_ivp(self, t_final, clip=False, ics=None, ics_sign=-1, **kwargs_for_solve_ivp):
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
        :arg ics_sign: The overall sign for the integrator initial conditions. Since the real
           LUCIDAC (REV1) has negating integrators as the classical integrators but the
           numerical simulation simulates this sign, a ``-1`` is correct here. Better don't
           touch it to remain compatible to the hardware.
        
        
        .. note::
        
           Clipping can have a weird effect in (very) linear problems because the underlying ODE
           Solver will be smart, evaluate the RHS seldomly and thus clipping does not happen
           fast enough, producing artefacts in the result. Therefore use it with care or make
           sure to make very small time steps.
        
        Quick usage example:
        
        >>> from lucipy import Circuit, Simulation
        >>> e = Circuit()
        >>> ramp  = e.int(ic = -1)  # makes an Integrator
        >>> const = e.const()       # makes a  Constant giver
        >>> e.connect(const, ramp, weight = 0.1)
        Route(uin=14, lane=16, coeff=0.1, iout=0)
        >>> result = Simulation(e).solve_ivp(500)
        >>> ramp_result = result.y[0] # unpack the first integrator output
        >>> plt.plot(result.t, ramp_result) # plot against solution times     # doctest: +SKIP
    
        If you are interested in the output which you can actually probe on LUCIDAC,
        i.e. the ADCs or Front panel output (ACLs), you can map the resulting state
        vector (at any soution time) throught :meth:`adc_values` and :meth:`acl_out_values`.        
        """
        import numpy as np
        if np.all(ics == None):
            ics = self.ics
        elif len(ics) < len(self.ics):
            ics = list(ics) + [0]*(len(self.ics) - len(ics))
            
        ics = ics_sign * np.array(ics)
        
        from scipy.integrate import solve_ivp
        return solve_ivp(lambda t,state: self.rhs(t,state,clip), [0, t_final], ics, **kwargs_for_solve_ivp)


def find(element, structure):
    """
    Simple path-based querying in a nested directory structure.
    """
    return functools.reduce(operator.getitem, element, structure)

def expose(f):
    "Decorator to mark a function or method as 'exposed'. Used in the simple Emulation registry"
    f.exposed = True
    return f

class EmulationError(Exception):
    """
    An error while handling a user request which eventually shall propagate
    towards the emulated registry to be served towards the client as a JSON
    envelope.
    """
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        super().__init__(msg)

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
       The error messages and codes returned by this emulator do not (yet) coincide with the
       error messages and codes from the real device.
    
    
    .. note::
        Since the overall code does not use asyncio as a philosophy, also this code is
        written as a very traditional forking server. In our low-volume practice, there
        should be no noticable performance penalty.
    
        If you choose a forking server, the server can handle multiple clients a time
        and is not "blocking" (the same way as the early real firmware embedded servers were).
        However, the "parallel server" in a forking (=multiprocessing) model also means
        that each client gets its own virtualized LUCIDAC due to the multiprocess nature (no
        shared address space and thus no shared LUCIDAC memory model) of the server.
    
    There are three usage modes of this class:
    
    - Directly using the emulator methods
    - Connection from :class:`~synchc.LUCIDAC` over *emulated socket*
    - Connection from any LUCIDAC JSONL client over TCP socket
    
    Direct usage means for instance
    
    >>> emu = Emulation()
    >>> print(emu.get_entities()) # doctest: +ELLIPSIS
    {'entities': {'70-79-74-68-6f-6e': {'/0': {'/M0': ...
    >>> emu.get_circuit()         # doctest: +ELLIPSIS
    {'entity': None, 'config': {'adc_channels': [], ...
    
    Given the nature of the JSONL protocol, this usage is *somewhat* as using :class:`~synchc.LUCIDAC`,
    in particular for setting/getting the circuit and starting a run. Note that this way, no JSON encoding
    takes place. This mode of operation is primarily useful for unit testing but otherwise does not
    fulfill the idea of the interface emulation.
    
    The emulated socket usage is like
    
    >>> from lucipy import LUCIDAC
    >>> hc = LUCIDAC("emu:/")
    >>> hc.get_entities()  # doctest: +ELLIPSIS
    {'70-79-74-68-6f-6e': {'/0': {'/M0': {'class': 2, ...
    
    Note that with this special endpoint URL syntax, even the socket is emulated and no TCP/IP connection
    is made. Again, this is ideal for unit testing because there is no headache with concurrently testing
    a server and a client. However, in this mode of operation the control flow remains at the client side
    and the event loop of the emulator is never triggered. This means that by practice there cannot happen
    real deviation from a simple query-response principle.
    
    The actual intended TCP/IP server usage is like
    
    >>> emu = Emulation(bind_port=0)
    >>> proc = emu.serve_forking()
    >>> endpoint = emu.endpoint()
    >>> endpoint               # doctest: +ELLIPSIS
    'tcp://127.0.0.1:...'
    >>> hc = LUCIDAC(endpoint)
    >>> hc.get_entities()  # doctest: +ELLIPSIS
    {'70-79-74-68-6f-6e': {'/0': {'/M0': {'class': 2, ...
    >>> hc.close()
    >>> proc.terminate() # stops the server process
    
    Note that by the nature of TCP/IP networking, the server can listen also at any other interface and
    thus can be reached from other computers and processes. In contrast, the previous usage examples were
    limited to the same python instance, they did not involve real networking.
    
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
        "Emulates the ping behaviour (approximatively)"
        return { "now": datetime.now().isoformat(), "micros": self.micros() }
        
    @expose
    def reset(self):
        """
        Resets the circuit configuration.
        As this models a LUCIDAC, the configuration holds a single cluster and some
        parts (but currently we don't emulate front panel and friends).
        """
        self.circuit = {
            "adc_channels": [],
            "acl_select": ["internal"]*8,
            '/0': {
                '/M0': {'elements': [ {'ic': 0, 'k': 10000} for i in range(8) ], },
                '/M1': {},
                '/U': {'outputs': [ None for i in range (32) ] },
                '/C': {'elements': [ 0 for i in range(32) ] },
                '/I': {
                    'outputs': [ None for i in range(16) ],
                    "upscaling": [False]*32,
                }
            }
        }
    
    @expose
    def reset_circuit(self):
        "Alias: Reset circuit configuration"
        return self.reset()
   
    @expose
    def get_circuit(self):
        """
        Read out circuit configuration
        """
        return {
            "entity": None, # sic!
            "config": self.circuit,
        }

    @expose
    def get_config(self):
        "Alias: Read out circuit configuration"
        return self.get_circuit()
    
    @expose
    def set_config(self, entity, config):
        """
        Set circuit configuration.
        
        Somewhat ironically, as in real LUCIDAC, this function does not comply if
        you try to set some nonexisting element. In the emulator, it just tries to
        update the local configuration which does not distinguish between entities
        and elements, anyway.
    
        :arg entity: A list such as ["AA-BB-CC-DD-EE-FF", "0", "/U"], i.e.
           the path to the entity. As the real LUCIDAC, we reject wrong carrier
           messages.
        :arg config: The configuration to apply to the entity.
        """
        if entity[0] != self.mac:
            return {"error": "Configuration for wrong (emulated) carrier"}
        if len(entity) == 1:
            self.circuit = config # carrier root level
            return
        
        # decorate things with slashes. Probably not very clever but at least
        # makes "0" to "/0". The protocol is just insane or very bad documented...
        # -> This will NOT work with carrier level settings!
        for i,e in enumerate(entity):
            if e[0] != "/":
                entity[i] = "/"+entity[i]
        try:
            parent = find(entity[1:-1], self.circuit)
            child_key = entity[-1]
        except KeyError as e:
            return {"error": "Asked for entity path {entity} but the following entity or element was not found: {e}"}
        parent[child_key] = config
        
    @expose
    def set_circuit(self, entity, config):
        "Alias: Set circuit configuration"
        return self.set_config(entity, config)
    
    
    default_run_config = {
        "halt_on_external_trigger": False,
        "halt_on_overload": False,
        "ic_time": 123456,
        "op_time": 123456,
    }
    
    default_daq_config = {
        "num_channels": 0,
        "sample_op": True,
        "sample_op_end": True,
        "sample_rate": 500_000,
    }
    
    #@expose("out-of-band")
    @expose
    def start_run(self, **start_run_msg):
        """
        Emulate an actual run with the LUCIDAC Run queue and FlexIO data aquisition.
        This will return the ADC measurements on the requested sampling points.
        There are no constraints for the sampling rate, in contrast to real LUCIDAC.
        
        This function does it all in one rush "in sync" , no need for a dedicated queue.
        Internally, it just prepares all envelopes and sends them out then alltogether.
        
        Current limitation: The emulator cannot make use of ACL_IN/OUT, i.e. the
        frontpanel analog inputs and outputs.
        
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
        

        """

        run_id = start_run_msg["id"]
        run_config = copy.deepcopy(self.default_run_config)
        daq_config = copy.deepcopy(self.default_daq_config)
        
        if "config" in start_run_msg:
            run_config.update({k: v for k, v in start_run_msg["config"].items() if k in run_config})
        if "daq_config" in start_run_msg:
            daq_config.update({k: v for k, v in start_run_msg["daq_config"].items() if k in daq_config})
        
        # extract most important things as shorthand
        t_final_ns = run_config["op_time"]
        t_final_sec = t_final_ns / 1e9
        samples_per_second = daq_config["sample_rate"]
        
        import numpy as np
        num_samples = int(t_final_sec * samples_per_second)
        sampling_times = np.linspace(0, t_final_sec, num_samples)
        
        reply_envelopes = []
        
        # the acknowledgement of the actual run query
        reply_envelopes.append({"type": "start_run", "msg": {} })
        
        from .circuits import Circuit
        circuit = Circuit().load(self.circuit)
        #print(circuit)
        #print(f"{t_final_sec=} {t_final_sec=} {samples_per_second=} {num_samples=} {sampling_times.shape=}")
        sim = Simulation(circuit, realtime=True)
        res = sim.solve_ivp(t_final_sec, dense_output=True)
        
        if res.status != 0:
            raise ValueError(f"ODE Solver failed: {res}")
        #assert data.t[-1] == t_final
        
        states_sampled = res.sol(sampling_times).T
        assert states_sampled.shape == (num_samples, 8)
        
        adc_samples = [sim.adc_values(state) for state in states_sampled]
        
        # Simulate a finite buffer
        typical_buffer_size_elements = 100
        num_messages = int(max(1, len(adc_samples) / typical_buffer_size_elements))
        if num_messages > 0:
            chunks = np.array_split(adc_samples, num_messages)
            for chunk in chunks:
                reply_envelopes.append({
                    "type": "run_data",
                    "msg": {
                        "id": run_id,
                        "entity": [ self.mac, "0" ],
                        "data": chunk.tolist(),
                    }
                })
                    
        reply_envelopes.append({"type": "run_state_change", "msg": { "id": run_id, "t": self.micros(), "old": "NEW", "new": "DONE" }})
        return reply_envelopes
    
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
    
    
    def handle_request(self, line, return_always_list=False):
        """
        Handles incoming JSONL encoded envelope and respons with a string encoded JSONL envelope.
   
        :param line: String encoded JSONL input envelope
        :param return_always_list: Returns always a list of strings
        :returns: String encoded JSONL single envelope. If out-of-bound messages are generated, will
          return a list of such strings.
        """
        
        # decided halfway to do it in another way
        #json_writer = (lambda envelope: writer((json.dumps(envelope)+"\n").encode("utf-8"))) if writer else None
        
        def decorate_protocol_reply(ret):
            if isinstance(ret["msg"], dict) and "error" in ret["msg"]:
                ret["error"] = ret["msg"]["error"]
                ret["msg"] = {}
                ret["code"] = -2
            else:
                ret["code"] = 0 
            
            return json.dumps(ret) + "\n"
        
        try:
            if not line or line.isspace():
                return "\n"
            envelope = json.loads(line)
            #print(f"Parsed {envelope=}")
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
                    if self.debug:
                        # fancy debugging, python included
                        import sys, traceback, pdb
                        extype, value, tb = sys.exc_info()
                        traceback.print_exc()
                        pdb.post_mortem(tb)
                    ret["msg"] = {"error": f"Error captured by handle_request(): {type(e).__name__}: {e}" }
            else:   
                ret["msg"] = {'error': "Don't know this message type"}
        except json.JSONDecodeError as e:
            ret = { "msg": { "error": f"Cannot read message '{line}', error: {e}" } }
        
        ret = decorate_protocol_reply(ret)
        return [ret] if return_always_list else ret
    
    def __init__(self, bind_addr="127.0.0.1", bind_port=5732, emulated_mac=default_emulated_mac, debug=False):
        """
        :arg bind_addr: Adress to bind to, can also be a hostname. Use "0.0.0.0" to listen on all interfaces.
        :art bind_port: TCP port to bind to. Use ``0`` to let the Operating System find a free port.
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
                        responses = parent.handle_request(line, return_always_list=True)
                        #print(f"Writing out {response=}")
                        #self.request.sendall(response.encode("ascii"))
                        
                        for res in responses:
                            self.wfile.write(res.encode("utf-8"))
                            
                        self.wfile.flush()
                    except (BrokenPipeError, KeyboardInterrupt) as e:
                        print(e)
                        return
        
        self.addr = (bind_addr, bind_port)
        self.handler_class = TCPRequestHandler
        self.debug = debug
        
    def _serve_forever(self):
        with self.server:
            self.obtained_addr = self.server.server_address
            print(f"Lucipy LUCIDAC Mockup Server listening at {self.endpoint()} - stop with CTRL+C")
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                print("Keyboard interrupt")
                self.server.server_close()
                return
            except Exception as e:
                print(f"Server crash: {e}")
                return
    
    def serve_forking(self):
        """
        Starts TCP server in a seperate process. Furthermore, the TCP Server will fork for each incoming
        connection, thus allowing multiple clients to connect at the same time. Since this distributed
        memory model cannot exchange information, each client sees its own version of a LUCIDAC.
        
        Returns a ``multiprocessing.Process`` class which can be asked for the process id, waited for,
        etc. Example:
        
        ::
        
            proc = emu.serve_forking()
            print(f"Waiting for server {emu.endpoint()} process to finish, can also do other work")
            proc.join()
        
        """
        class TCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
            pass
        self.server = TCPServer(self.addr, self.handler_class)
        self.obtained_addr = self.server.server_address
        proc = multiprocessing.Process(target=self.server.serve_forever)
        proc.start()
        return proc
    
    def serve_threading(self):
        """
        Starts TCP server in a seperate thread. Furthermore, the TCP Server will reply to each incoming
        connection in a seperate thread. Theoretically this could give each client a view to a common
        hardware memory model (not taking into account locking etc.)
        
        Yields the running thread from a context manager, thus allows to continue work, also
        with the thread as well as the Emulation object in main thread.
        
        ::
        
            emu = Emulation(bind_addr="0.0.0.0", bind_port=0)
            thread = next(emu.serve_threading())
            print(f"Waiting for server {emu.endpoint()} thread to finish, can also do other work")
            thread.join()
        
        .. warning::
        
           There is still some bug here and the server started within a thread never responds.
        """
        class TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            pass
        self.server = TCPServer(self.addr, self.handler_class)
        
        with self.server:
            self.obtained_addr = self.server.server_address
            thread = threading.Thread(target=self.server.serve_forever)
            thread.daemon = True # exit when main thread terminates
            thread.start()
            print(f"Lucipy LUCIDAC Mockup Server started in background thread at {self.endpoint()}")
            yield thread
        
        return self
    
    def serve_blocking(self):
        """
        Starts TCP server in main thread. This hands over control to the socket server event queue.
        Only one client can connect at a time. The function will never return except user interaction.        
        """
        class TCPServer(socketserver.TCPServer):
            pass
        self.server = TCPServer(self.addr, self.handler_class)
        self._serve_forever() # will never return except exception
    
    def endpoint(self):
        """
        Determines endpoint URL if some server has been started. Endpoints are Strings.
        If a server has been started, this returns the actual Port assigned if port ``0`` was requested.
        """
        ip, port = self.obtained_addr if hasattr(self, "obtained_addr") else self.addr
        return f"tcp://{ip}:{port}"

        
