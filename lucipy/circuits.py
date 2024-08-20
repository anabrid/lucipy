#!/usr/bin/env python3

"""
Lucipy Circuits: A shim over the routes.

This class structure provides a minimal level of user-friendlyness to allow
route-based programming on the LUCIDAC. This effectively means a paradigm
where one connects elements from math blocks to each other, with a coefficient
inbetween. And the assignment throught the UCI matrix is done greedily by
"first come, first serve" without any constraints.

The code is heavily inspired by the LUCIGUI lucisim typescript compiler,
which is however much bigger and creates an AST before mapping.

In contrast, the approach demonstrated here is not even enough for REV0 connecting
ExtIn/ADC/etc. But it makes it very simple and transparent to work with routes
and setup the circuit configuration low level.
"""

import functools, operator, textwrap, pprint, itertools, random
from collections import namedtuple
from typing import get_args, List, Dict, Union, Optional

# like sum(lst, []) but accepts generators instead of lists
flatten = lambda lst: functools.reduce(operator.iconcat, lst, [])
find = lambda crit, default, lst: next((x for x in lst if crit(x)), default)
clean = lambda itm: [ k[0] if len(k)==1 else (None if len(k)==0 else k) for k in itm ]

def window(seq, n=2):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(itertools.islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


def next_free(occupied: List[bool], append_to:int=None) -> Optional[int]:
    """
    Looks for the first False value within a list of truth values.

    >>> next_free([1,1,0,1,0,0]) # using ints instead of booleans for brevety
    2

    If no more value is free in list, it can append up to a given value

    >>> next_free([True]*4, append_to=3) # None, nothing free
    >>> next_free([True]*4, append_to=6)
    4
    """
    for idx, val in enumerate(occupied):
        if not val:
            return idx
    return len(occupied) if append_to != None and len(occupied) < append_to else None

# "in" is a reserved keyword in python, so all inputs are called a,b,c,... even if there is ony one

Int = namedtuple("Int", ["id", "out", "a"])
Mul = namedtuple("Mul", ["id", "out", "a", "b"])
Const = namedtuple("Const", ["id", "out" ])
Ele = Union[Int,Mul,Const]


class DefaultLUCIDAC:
    num_int = 8
    num_mul = 4
    num_const = 4 # REV0 has constant givers
    
    MMulOffset = 0 # M1 block
    MIntOffset = num_mul + num_const # == 8 # M0 block

    @staticmethod
    def reservoir(default_value=False):
        return {
            Int: [default_value]*DefaultLUCIDAC.num_int,
            Mul: [default_value]*DefaultLUCIDAC.num_mul,
            Const: [default_value]*DefaultLUCIDAC.num_const,
        }
    
    @classmethod
    def make(cls, t:Ele, idx):
        """
        A factory for the actual elements.
    
        >>> DefaultLUCIDAC().make(Int, 1)
        Int(id=1, out=9, a=9)
        >>> DefaultLUCIDAC().make(Mul, 3)
        Mul(id=3, out=3, a=6, b=7)
        """
        if t == Int:
            return Int(idx, cls.MIntOffset+idx, cls.MIntOffset+idx)
        if t == Mul:
            return Mul(idx, 
                cls.MMulOffset + idx,
                cls.MMulOffset + 2*idx,
                cls.MMulOffset + 2*idx+1)
        if t == Const:
            # REV0 constants at MMul block
            return Const(idx, cls.MMulOffset + idx + cls.num_mul)
        
    @staticmethod
    def populated():
        "An unsorted list of all allocatable computing elements"
        return flatten([ [ DefaultLUCIDAC.make(t,i) for i,_ in enumerate(v) ] for t,v in DefaultLUCIDAC.reservoir().items() ])
    
    
    @classmethod
    def resolve_mout(cls, idx, reservoir):
        """
        Simplistic way to map mul block outputs to a reservoir
        """
        if idx < 0:  raise ValueError(f"0 < {idx=} < 16 too small")
        if idx < 4:  return reservoir[Mul][idx]
        if idx < 8:  return reservoir[Const][idx - cls.num_mul]
        if idx < 16: return reservoir[Int][idx - cls.MIntOffset]
        else:        raise ValueError(f"0 < {idx=} < 16 too large")

class Reservoir:
    """
    This is basically the entities list, tracking which one is already
    handed out ("allocated") or not.

    Note that the Mul/Int classes only hold some integers. In contrast, the
    configurable properties of the stateful computing element (Integrator)
    is managed by the MIntBlock class below.
    """
    allocated: Dict[Ele,List[bool]]
    
    def __init__(self, allocation=None, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        # an idea was to look that up as in luci.get_entities(), however now we keep it simple
        self.allocated = DefaultLUCIDAC.reservoir() if not allocation else allocation


    def alloc(self, t:Ele, id=None):
        """
        Allocate computing elements.
        
        >>> r = Reservoir()
        >>> r.alloc(Int,1)
        Int(id=1, out=9, a=9)
        >>> r.alloc(Int)
        Int(id=0, out=8, a=8)
        >>> r.alloc(Int)
        Int(id=2, out=10, a=10)
        """
        try:
            lst = self.allocated[t]
            idx = id if id != None else next_free(lst)
            if idx == None:
                raise ValueError(
                    f"No more free Computing Elements for type {t}, all {len(lst)} occupied!"
                    if id != None else
                    f"Compute Element {t} number {id} is already allocated")
            self.allocated[t][idx] = True
            return DefaultLUCIDAC.make(t, idx)
        except KeyError:
            raise TypeError(f"Computing Element Type {t} not supported. Valid ones are {', '.join(map(str, self.allocated.keys()))}")
        except IndexError:
            raise ValueError(f"Have only {len(allocated[t])} Computing Elements of Type {t} available, inexistent id {id} requested.")

    # TODO: Rename to "integrator" in order to make sure
    #       it is not misunderstood as "integration"
    def int(self, id=None):
        "Allocate an Integrator. If you pass an id, allocate that particular integrator."
        return self.alloc(Int, id)

    # TODO: Rename to "multiplier" in order to make sur
    #       it is not misunderstood as "multiplication"
    def mul(self, id=None):
        "Allocate a Multiplier. If you pass an id, allocate that particular multiplier."
        return self.alloc(Mul, id)
    
    def const(self, id=None):
        return self.alloc(Const, id)
    
    # some more fun
    def ints(self, count):
        "Allocate count many integrators"
        return [self.int() for x in range(count)]

    def muls(self, count):
        "Allocate count many multipliers"
        return [self.mul() for x in range(count)]


Route = namedtuple("Route", ["uin", "lane", "coeff", "iout"])

def Connection(source:Union[Ele,int], target:Union[Ele,int], weight=1):
    """
    Transforms an argument list somewhat similar to a "logical route" in the
    lucicon code to a physical route.
        
    >>> r = Reservoir()
    >>> I1, M1 = r.int(), r.mul()
    >>> Connection(M1.a, I1)
    Route(uin=0, lane=None, coeff=1, iout=8)

    """
    if isinstance(source, get_args(Ele)):
        source = source.out
    if isinstance(target, get_args(Ele)):
        # TODO this should spill out an error if the Ele has more then one inputs
        target = target.a
    return Route(source, None, weight, target)

class MIntBlock:
    """
    Stateful configuration about all the MIntBlock.
    """
    #ics : List[float]
    #k0s : List[int]
    
    slow =    100
    fast = 10_000
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.ics = [0.0]*DefaultLUCIDAC.num_int
        self.k0s = [self.fast]*DefaultLUCIDAC.num_int
        
    def randomize(self):
        for i in range(DefaultLUCIDAC.num_int):
            self.ics[i] = random.uniform(-1.0, +1.0)
            self.k0s[i] = random.choice([self.slow, self.fast])

    def set_ic(self, el:Union[Int,int], val:float):
        el = el.id if isinstance(el, Int) else el
        self.ics[el] = val
    
    def set_k0(self, el:Union[Int,int], val:float):
        el = el.id if isinstance(el, Int) else el
        self.k0s[el] = val
        
    def generate(self):
        return {
            "elements": [dict(k=k, ic=ic) for k,ic in zip(self.k0s, self.ics)]
        }

    def load(self, config):
        for idx, integrator in enumerate(config["elements"]):
            if "k" in integrator:
                self.k0s[i] = integrator["k"]
            if "ic" in integrator:
                self.ics[i] = integrator["ics"]
    
    def to_pybrid_cli(self):
        """
        Generate the Pybrid-CLI commands as string out of this Route representation
        """
        ret = []
        ret += [f"set-element-config carrier/0/M0/{i} ic {val}" for i,val in enumerate(self.ics) if val != 0]
        ret += [f"set-element-config carrier/0/M0/{i} k {val}" for i,val in enumerate(self.ics) if self.k0s != self.fast]
        return "\n".join(ret)

#: Just a tuple collecting U, C, I matrices without determining their actual representation.
#: The representation could be lists, numpy arrays, etc. depending on the use.
UCI = namedtuple("UCI", ["U", "C", "I"])

class Routing:
    """
    This class provides a route-tuple like interface to the UCI block and
    generates the Output-centric matrix configuration at the end.
    """
    max_lanes = 32
    #routes : List[Route]
    
    def available_lanes(self):
        # for a fully functional lucidac, do this:
        return list(range(32))
        # Instead, we know these lanes are working only:
        #return [0,1,2,3,4,5, 14,15, 16,17, 18,19, 20,21, 30,31]
    
    def __repr__(self):
        return f"Routing({pprint.pformat(self.routes)})"
    
    def __init__(self, routes: List[Route] = None, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.routes = routes if routes else []
    
    def randomize(self, num_lanes=32, max_coeff=+10, seed=None):
        """
        Appends random routes.
    
        :arg num_lanes: How many lanes to fill up. By default fills up all lanes.
        :arg max_coeff: Maximal coefficient magnitudes. ``+1`` or ``+10`` are
             useful values for LUCIDAC.
        :arg seed: For reproducability (as in unit tests), this calls ``random.seed``.
             A large integer may be a suitable argument.
        :returns: The instance, i.e. is chainable.
        """
        if seed:
            random.seed(seed)
        for lane in range(num_lanes):
            uin, iout = random.randrange(16), random.randrange(16)
            coeff = random.uniform(-abs(max_coeff), +abs(max_coeff))
            self.add( Route(uin, lane, coeff, iout) )
        return self
    
    def next_free_lane(self):
        route_for_lane = [ find(lambda r: r.lane == lane, None, self.routes) for lane in self.available_lanes() ]
        is_lane_occupied = [ True if x else False for x in route_for_lane ]
        #print("next_free_lane", self.available_lanes())
        #print("next_free_lane", is_lane_occupied)
        #occupied_lanes = [ r.lane for r in self.routes ]
        idx = next_free(is_lane_occupied)#, append_to=self.max_lanes)
        #print("next_free_lane = ",idx)
        if idx == None:
            raise ValueError(f"All {self.available_lanes()} available lanes occupied, no more connections possible.")
        return self.available_lanes()[idx]
    
    def add(self, route_or_list_of_routes:Union[Route,List[Route]]):
        if isinstance(route_or_list_of_routes, list):
            return list(map(self.add, route_or_list_of_routes))
        route = route_or_list_of_routes
        if route.lane == None:
            physical = Route(route.uin, self.next_free_lane(), route.coeff, route.iout)
        else:
            if route.lane in [ r.lane for r in self.routes ]:
                raise ValueError("Cannot append {route} because this lane is already occupied.")
            physical = route
        self.routes.append(physical)
        return physical

    def connect(self, source:Union[Ele,int], target:Union[Ele,int], weight=1):
        return self.add(Connection(source,target,weight))
    
    def routes2input(self) -> UCI:
        """
        Converts the list of routes to an *input matrix representation*. In this format,
        the U/C/I matrix are each represented as a list of 32 numbers.
        This is basically an array-of-structures to structure-of-array (AoS-to-SoA) operation
        and inspired by the *lucicon* circuit compiler (part of `lucigui <https://github.com/anabrid/lucigui>`_).    
        See :meth:`generate` for the actual high-level method for the spare matrix format used
        by the LUCIDAC protocol.
    
        .. warning::
    
           The C matrix values in this representation are floats within ``[-20,+20]`` and not
           yet rescaled (as in REV1 hardware). See :meth:`coeff_upscale` for the code which shifts
           this information.
    
        """
        return UCI(
            U=clean([[r.uin  for r in self.routes if r.lane == lane] for lane in range(32)]),
            I=clean([r.iout for r in self.routes if r.lane == lane] for lane in range(32)),
            C=[route.coeff if route else 0 for route in (find(lambda r, lane=lane: r.lane == lane, None, self.routes) for lane in range(32))]
        )
    
    @staticmethod
    def input2output(inmat, keep_arrays=True):
        "Maps Array<int,32> onto Array<Array<int>|int, 16>"
        output = [[] for _ in range(16)] # Array<Array, 16>
        for lane, clane in enumerate(inmat):
            if clane != None:
                if isinstance(clane, list):
                    for ci in clane:
                        output[ci].append(lane)
                else:
                    output[clane].append(lane)
        return output if keep_arrays else clean(output)
    
    @staticmethod
    def output2input(outmat):
        "Maps Array<Array<int>|int,16> onto Array<int,32>"
        input = [ None for _ in range(32) ]
        for clane, lanes in enumerate(outmat):
            if lanes:
                for lane in lanes:
                    input[clane] = clane
        return input
    
    @staticmethod
    def coeff_upscale(c_elements):
        upscaling = [ (v < -1 or v > 1) for v in c_elements ]
        scaled_c = [ (c/10 if sc else c) for sc, c in zip(upscaling, c_elements) ]
        return upscaling, scaled_c

    def generate(self):
        """
        Generate the configuration data structure required by the protocol, which is
        that "output-centric configuration".
        """
        U,C,I = self.routes2input()
        upscaling, scaled_c = self.coeff_upscale(C)
        return {
            "/U": dict(outputs = U),
            "/C": dict(elements = scaled_c),
            "/I": dict(outputs = self.input2output(I), upscaling = upscaling)
        }
        # TODO: Ublock Altsignals, where in REV1?
        # ret["/U"]["alt_signals"] = [False]*8
        
    def load(self, config):
        # load all in output centric format
        U = config["/U"] if "/U" in config else [ None ]*32
        C = config["/C"] if "/C" in config else [ 0.0  ]*32
        I = config["/I"] if "/I" in config else [ None ]*16
        I = self.output2input(I)
        
        for lane,(u,c,i) in enumerate(zip(U,C,I)):
            self.add(Route(u,lane,c,i))
    
    def to_pybrid_cli(self):
        """
        Generate the Pybrid-CLI commands as string out of this Route representation.
        """
        return "\n".join(f"route -- carrier/0 {r.uin:2d} {r.lane:2d} {r.coeff: 7.3f} {r.iout:2d}" for r in self.routes)
    
    def to_dense_matrix(self):
        """
        Generates a dense numpy matrix for the UCI block, i.e. a real-valued 16x16 matrix with
        bounded values [-20,20] where at most 32 entries are non-zero.
        """
        import numpy as np
        UCI = np.zeros((16,16))
        for (uin, _lane, coeff, iout) in self.routes:
            UCI[iout,uin] += coeff
        return UCI
    
    def to_dense_matrices(self, ui_dtype=bool) -> UCI:
        """
        Generates the three matrices U, C, I as dense numpy matrices.
        
        :arg ui_dtype: Data type for the U and I matrix. Naturally, this are
          bitmatrices, so the default ``bool`` is a suitable choise. If you
          prefer to look at numbers, say ``int`` or ``float`` instead.
          Do not worry, numpy otherwise does the same arithmetics with booleans
          as with integers.
        :returns: 3-Tuple of numpy matrices for U, C, I, in this order.
        
        Note that one way to reproduce :meth:`to_dense_matrix` is just by
        computing ``I.dot(C.dot(U))`` on the output of this function.
        
        >>> import numpy as np
        >>> c = Circuit().randomize()
        >>> U, C, I = c.to_dense_matrices()
        >>> np.all(I.dot(C.dot(U)) == c.to_dense_matrix())
        True
        """
        import numpy as np
        U = np.zeros((32,16), dtype=ui_dtype)
        C = np.zeros((32,32))
        I = np.zeros((16,32), dtype=ui_dtype)
        
        for (uin, lane, coeff, iout) in self.routes:
            U[lane, uin]  = 1
            C[lane, lane] = coeff
            I[iout, lane] = 1
        
        return UCI(U,C,I)

    def to_sympy(self, int_names=None, subst_mul=False, no_func_t=False):
        """
        Creates an ODE system in sympy based on the circuit.
        
        :arg int_names: Allows to overwrite the names of the integators. By default they
           are called i_0, i_1, ... i_7. By providing a list such as ["x", "y", "z"], these
           names will be taken. If the list is shorter then length 8, it will be filled up
           with the default names.
        :arg subst_mul: Substitute multiplications, getting rid of explicit Eq(m_0, ...)
           statements. Useful for using the equation set within an ODE solver because the
           state vector is exactly the same length of the entries.
        :arg no_func_t: Write f instead of f(t) on the RHS, allowing for denser notations,
           helps also in some solver contexts.
        
        .. warning ::
        
           This method is part of the Routing class and therefore knows nothing about
           the MIntBlock settings, in particular not the k0. You have to apply different
           k0 values by yourself if neccessary! This can be as easy as to multiply the
           equations rhs with the appropriate k0 factor.
        
        Further limitations:
        
        * Will just ignore ACL_IN (Front panel in/out)
        
        Example for making use of the output within a scipy solver:
        
        ::
        
            from sympy import latex, lambdify, symbols
            from scipy.integrate import solve_ivp
            xyz = list("xyz")
            eqs = lucidac_circuit.to_sympy(xyz, subst_mul=True, no_func_t=True)
            print(eqs)
            print(latex(eqs))
            rhs = [ e.rhs for e in eqs ]
            x,y,z = symbols(xyz)
            f = lambdify((x,y,z), rhs)
            f(1,2,3) # works
            sol = solve_ivp(f, (0, 10), [1,2,3])
        
        """
        
        from sympy import symbols, Symbol, Function, Derivative, Eq
        
        t = symbols("t")
        
        int_default_names = [ f"i_{d}" for d in range(8) ]
        if int_names:
            for i,n in enumerate(int_names):
                int_default_names[i] = n
        
        ints = [Function(n)(t) for n in int_default_names]
        muls = [Function(f"m_{d}")(t) for d in range(4)]
        sympy_reservoir = { Int: ints, Mul: muls, Const: [1.0]*4 }
        di = [ Derivative(i, t) for i in ints ]
        
        sympy_uin = [ DefaultLUCIDAC.resolve_mout(route.uin, sympy_reservoir) for route in self.routes ]
        #summands = [ coeff * DefaultLUCIDAC.resolve_mout(uin, sympy_reservoir) for (uin, _lane, coeff, iout) in self.routes ]
        min_sums = [ sum(route.coeff*uin_symbol for uin_symbol, route in zip(sympy_uin, self.routes) if route.iout == min) for min in range(16) ]
        
        min_inputs = itertools.batched(range(0,8), 2) # [(0, 1), (2, 3), (4, 5), (6, 7)]
        
        # these will contain still-to-filter entries like Eq(m_3(t),0)
        mul_eqs = [ Eq(mi, -(min_sums[input_indices[0]] * min_sums[input_indices[1]])) for mi, input_indices in zip(muls, min_inputs) ]
        int_eqs = [ Eq(di[idx], min_sums[idx+DefaultLUCIDAC.MIntOffset]) for idx in range(0,8) ]
        
        if subst_mul:
            mappings = { eq.lhs: eq.rhs for eq in mul_eqs }
            # replace recursive calls such as in m0=x*x, my=x*m0
            mappings = { eq.lhs: eq.rhs.subs(mappings) for eq in mul_eqs }
            # then apply on int definitions
            eqs = [ eq.subs(mappings) for eq in int_eqs ] 
        else:
            eqs = mul_eqs + int_eqs
            
        if no_func_t:
            mappings = { Function(n)(t): Symbol(n) for n in int_default_names }
            eqs = [ eq.subs(mappings) for eq in eqs]
            
        return [ eq for eq in eqs if eq.rhs != 0 ]
    
    def reverse(self):
        """
        Trivially "reverse engineer" a circuit based on routes
        """
        
        # TODO: Code is ugly, refactor to proper Int/Mul types which can do most of this
        
        def assert_one(candidates, r):
            candidates = list(candidates)
            if len(candidates) == 0:
                raise ValueError(f"Route {r} not assignable, no candidates")
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) == 2:
                raise ValueError(f"Route {r} overassignable, candidates are {src_candidates}")
        
        populated = DefaultLUCIDAC.populated()
        
        def within(itm, fields, idx):
            for n in fields:
                if hasattr(itm, n) and getattr(itm, n) == idx:
                    return n
            return None

        def route2connection(r):
            # TODO Warning, the target Mul.a|b is most likely still wrong. Has to be tested,
            #      see for instance roessler or neuron as an errnous example.
            
            #print("source ", r)
            source = assert_one(filter(lambda itm: itm.out == r.uin, populated), r)
            #print("target ", r)
            target = assert_one(filter(lambda itm: bool(within(itm, ["a", "b"], r.iout)), populated), r)
            target_port = assert_one(filter(bool, [ within(itm, ["a", "b"], r.uin) for itm in populated ]), r)
            has_two_ports = hasattr(target, "b") # i.e. if it is Mul or Not
            weight = r.coeff
            source_shortname = type(source).__name__ + str(source.id)
            target_shortname = type(target).__name__ + str(target.id) + ("."+target_port if has_two_ports else "")
            return f"Connection(" + source_shortname + ", " + target_shortname + (f", {weight=}" if r.coeff != 1 else "") + ")"
                         
        return ",\n".join(map(route2connection, self.routes))
        
class Probes:
    """
    Models the LUCIDAC Carrier ADC channels and Front Panel inputs (ACL_select).
    """
    
    def __init__(self, acl_select=None, adc_channels=None, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.acl_select = acl_select if acl_select else []
        self.adc_channels = adc_channels if adc_channels else []
        
    def set_acl_select(self, acl_select):
        self.acl_select = acl_select
        
    def set_adc_channels(self, adc_channels):
        self.adc_channels = adc_channels
        
    def generate(self):
        ret = {}
        if self.acl_select:
            #if not all(isinstance(v, bool) for v in self.acl_select):
            #    raise ValueError(f"Unsuitable ACL selects, expected list of bools: {self.acl_select}")
            ret["acl_select"] = self.acl_select
        if self.adc_channels:
            if not all(isinstance(v, int) for v in self.adc_channels):
                raise ValueError(f"Unsuitable ADC channels, expected list of ints: {self.adc_channels}")
            ret["adc_channels"] = self.adc_channels
        return ret

class Circuit(Reservoir, MIntBlock, Routing, Probes):
    """
    A one stop-shop of a compiler! This class collects all independent behaviour in a neat
    single-class interface. This allows it, for instance, to provide an improved version of
    the Reservoir's int() method which also sets the Int state in one go.
    It also can generate the final configuration format required for LUCIDAC.
    """
    
    def __init__(self, routes: List[Route] = []):
        super().__init__(routes=routes)
        self.u_constant = False
    
    def int(self, *, id=None, ic=0, slow=False):
        "Allocate an Integrator and set it's initial conditions and k0 factor at the same time."
        el = Reservoir.int(self, id)
        self.set_ic(el, ic)
        self.set_k0(el, MIntBlock.slow if slow else MIntBlock.fast)
        return el
    
    def use_constant(self, use_constant=True):
        """
        Useful values for the constant:
    
        * ``True`` or ``1.0`` or ``1``: Makes a constant ``+1``
        * ``0.1`` makes such a constant
        * ``False`` or ``None`` removes the overall constant
        """
        self.u_constant = use_constant
    
    def load(self, config_message):
        """
        Loads the configuration which :meth:`generate` spills out. The full circle.
        """
        config = config_message["config"] if "config" in config_message else config_message
        config = config["/0"] if "/0" in config else config
        
        if "/M0" in config:
            MIntBlock.load(config["/M0"])
        
        Routing.load(config)
        # Probes.load(config)
    
    def randomize(self, num_lanes=32, max_coeff=+10, seed=None):
        """
        Add random configurations. This function is basically only for
        testing. See :meth:`Routing.randomize` for the paramters.
    
        :arg num_lanes: How many lanes to fill up. By default fills up all lanes.
        :arg max_coeff: Maximal coefficient magnitudes. ``+1`` or ``+10`` are
             useful values for LUCIDAC.
        :arg seed: For reproducability (as in unit tests), this calls ``random.seed``.
             A large integer may be a suitable argument.
        :returns: The instance, i.e. is chainable.
        """
        MIntBlock.randomize(self)
        Routing.randomize(self, num_lanes, max_coeff, seed)
        return self
    
    def generate(self):
        """
        Returns the data structure required by the LUCIDAC set_config call *for a given carrier*,
        i.e. usage is like 
    
        ::
    
            outer_config = {
                "entity": ["04-E9-E5-16-09-92", "0"],
                "config": circuit.generate()
            }
            hc.query("set_config", outer_config)
        """
        cluster_config = Routing.generate(self)
        cluster_config["/M0"] = MIntBlock.generate(self) 
        cluster_config["/M1"] = {} # MMulBlock
        
        # update with Carrier configuration
        cluster_config.update(Probes.generate(self).items())
        
        # send constant configuration regardless of it's value, because
        # False and None are also valid.
        cluster_config["/U"]["constant"] = self.u_constant
            
        return cluster_config 
        
    def write(self, hc):
        hc.set_circuit(self.generate())
        
    def to_pybrid_cli(self):
        nl = "\n"
        ret = "set-alias * carrier" + nl*2
        ret += MIntBlock.to_pybrid_cli(self) + nl
        
        ret += Routing.to_pybrid_cli(self) + nl
        
        ret += "# run --op-time 500000" + nl
        return ret
