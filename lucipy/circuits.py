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

import functools, operator
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
Ele = Int|Mul

class DefaultLUCIDAC:
    num_int = 8
    num_mul = 4

    @staticmethod
    def reservoir(default_value=False):
        return {
            Int: [default_value]*DefaultLUCIDAC.num_int,
            Mul: [default_value]*DefaultLUCIDAC.num_mul,
        }
    
    @staticmethod
    def make(t:Ele, idx):
        """
        A factory for the actual elements.
    
        >>> Reservoir().make(Int, 1)
        Int(id=1, out=1, a=1)
        >>> Reservoir().make(Mul, 3)
        Mul(id=3, out=3, a=6, b=7)
        """
        if t == Int:
            return Int(idx,idx,idx)
        if t == Mul:
            return Mul(idx,idx, 2*idx, 2*idx+1)
    

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
        Int(id=1, out=1, a=1)
        >>> r.alloc(Int)
        Int(id=0, out=0, a=0)
        >>> r.alloc(Int)
        Int(id=2, out=2, a=2)
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
    Route(uin=0, lane=None, coeff=1, iout=0)

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
    ics : list[float]
    k0s : list[int]
    
    slow =  1_000
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


class Routing:
    """
    This class provides a route-tuple like interface to the UCI block and
    generates the Output-centric matrix configuration at the end.
    """
    max_lanes = 32
    routes : list[Route]
    
    def __repr__(self):
        return f"Routing({routes})"
    
    def __init__(self, routes: list[Route] = [], **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.routes = routes
    
    def next_free_lane(self):
        occupied_lanes = [ True if x else False for x in (find(lambda r: r.lane == lane, None, self.routes) for lane in range(32))]
        #occupied_lanes = [ r.lane for r in self.routes ]
        idx = next_free(occupied_lanes, append_to=self.max_lanes)
        if idx == None:
            raise ValueError(f"All {self.max_lanes} available lanes occupied, no more connections possible.")
        return idx
    
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
        self.add(Connection(source,target,weight))
    
    @staticmethod
    def routes2matrix(routes):
        "AoS->SoA Reduced Matrix (=input) representation, as in lucidon/mapping.ts"
        return dict(
            u=clean([[r.uin  for r in routes if r.lane == lane] for lane in range(32)]),
            i=clean([r.iout for r in routes if r.lane == lane] for lane in range(32)),
            c=[route.coeff if route else 0 for route in (find(lambda r, lane=lane: r.lane == lane, None, routes) for lane in range(32))]
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
        mat = self.routes2matrix(self.routes)
        return {
            "/U": dict(outputs = mat["u"]),
            "/C": dict(elements =  mat["c"]),
            "/I": dict(outputs = self.input2output(mat["i"]))
        }
        # TODO: Ublock Altsignals, where in REV1?
        # ret["/U"]["alt_signals"] = [False]*8


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
        "Returns the data structure required by the LUCIDAC set_config call"
        config = {
            "/0": {
                "/M0": MIntBlock.generate(self),
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
