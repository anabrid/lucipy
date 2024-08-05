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

import functools, operator, textwrap, pprint
from collections import namedtuple
from typing import get_args

# like sum(lst, []) but accepts generators instead of lists
flatten = lambda lst: functools.reduce(operator.iconcat, lst, [])
find = lambda crit, default, lst: next((x for x in lst if crit(x)), default)
clean = lambda itm: [ k[0] if len(k)==1 else (None if len(k)==0 else k) for k in itm ]

def next_free(occupied: list[bool], append_to:int=None) -> int|None:
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
Ele = Int|Mul|Const


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

class Reservoir:
    """
    This is basically the entities list, tracking which one is already
    handed out ("allocated") or not.

    Note that the Mul/Int classes only hold some integers. In contrast, the
    configurable properties of the stateful computing element (Integrator)
    is managed by the MIntBlock class below.
    """
    allocated: dict[Ele,list[bool]]
    
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

    def int(self, id=None):
        "Allocate an Integrator. If you pass an id, allocate that particular integrator."
        return self.alloc(Int, id)

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

def Connection(source:Ele|int, target:Ele|int, weight=1):
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
    #ics : list[float]
    #k0s : list[int]
    
    slow =    100
    fast = 10_000
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.ics = [0.0]*DefaultLUCIDAC.num_int
        self.k0s = [self.fast]*DefaultLUCIDAC.num_int
        
    def set_ic(self, el:Int|int, val:float):
        el = el.id if isinstance(el, Int) else el
        self.ics[el] = val
    
    def set_k0(self, el:Int|int, val:float):
        el = el.id if isinstance(el, Int) else el
        self.k0s[el] = val
        
    def generate(self):
        return {
            "elements": [dict(k=k, ic=ic) for k,ic in zip(self.k0s, self.ics)]
        }
    
    def to_pybrid_cli(self):
        """
        Generate the Pybrid-CLI commands as string out of this Route representation
        """
        ret = []
        ret += ["set-element-config carrier/0/M0/{i} ic {val}" for i,val in enumerate(self.ics) if val != 0]
        ret += ["set-element-config carrier/0/M0/{i} k {val}" for i,val in enumerate(self.ics) if k0s != self.fast]
        return "\n".join(ret)

class Routing:
    """
    This class provides a route-tuple like interface to the UCI block and
    generates the Output-centric matrix configuration at the end.
    """
    max_lanes = 32
    #routes : list[Route]
    
    def available_lanes(self):
        # for a fully functional lucidac, do this:
        #return range(32)
        # Instead, we know these lanes are working only:
        return [0,1,2,3,4,5, 14,15, 16,17, 18,19, 20,21, 30,31]
    
    def __repr__(self):
        return f"Routing({pprint.pformat(self.routes)})"
    
    def __init__(self, routes: list[Route] = None, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.routes = routes if routes else []
    
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
    
    def add(self, route_or_list_of_routes:Route|list[Route]):
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

    def connect(self, source:Ele|int, target:Ele|int, weight=1):
        return self.add(Connection(source,target,weight))
    
    def routes2matrix(self):
        """
        AoS->SoA Reduced Matrix (=input) representation, as in lucidon/mapping.ts
        These are the spare matrix formats used by the protocol.
        """
        return dict(
            u=clean([[r.uin  for r in self.routes if r.lane == lane] for lane in range(32)]),
            i=clean([r.iout for r in self.routes if r.lane == lane] for lane in range(32)),
            c=[route.coeff if route else 0 for route in (find(lambda r, lane=lane: r.lane == lane, None, self.routes) for lane in range(32))]
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
        

    def generate(self):
        """
        Generate the configuration data structure required by the protocol, which is
        that "output-centric configuration".
        """
        mat = self.routes2matrix()
        return {
            "/U": dict(outputs = mat["u"]),
            "/C": dict(elements =  mat["c"]),
            "/I": dict(outputs = self.input2output(mat["i"]))
        }
        # TODO: Ublock Altsignals, where in REV1?
        # ret["/U"]["alt_signals"] = [False]*8
    
    def to_pybrid_cli(self):
        """
        Generate the Pybrid-CLI commands as string out of this Route representation
        """
        return "\n".join("route -- carrier/0 {r.uin:2d} {r.lane:2d} {r.coeff: 7.3f} {r.iout:2d}" for r in self.routes)
    
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
        


class Circuit(Reservoir, MIntBlock, Routing):
    """
    A one stop-shop of a compiler! This class collects all independent behaviour in a neat
    single-class interface. This allows it, for instance, to provide an improved version of
    the Reservoir's int() method which also sets the Int state in one go.
    It also can generate the final configuration format required for LUCIDAC.
    """
    
    def __init__(self, routes: list[Route] = []):
        super().__init__(routes=routes)
    
    def int(self, *, id=None, ic=0, slow=False):
        "Allocate an Integrator and set it's initial conditions and k0 factor at the same time."
        el = Reservoir.int(self, id)
        self.set_ic(el, ic)
        self.set_k0(el, MIntBlock.slow if slow else MIntBlock.fast)
        return el
    
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
        return cluster_config 
    
        config = {
            "/0": {
                "/M0": MIntBlock.generate(self) ,
                "/M1": {},
            }
        }
        # update with U, C, I
        config["/0"] = {**config["/0"], **Routing.generate(self)}

        # return full message for set_circuit query.
        return {
            "entity": None,
            "config": config
        }
    
    def write(self, hc):
        hc.set_circuit(self.generate())
        
    def to_pybrid_cli(self):
        return textwrap.dedent(f"""
        set-alias * carrier
        
        {MIntBlock.to_pybrid_cli(self)}
        
        {Routing.to_pybrid_cli(self)}
        
        # run --op-time 500000
        """)
