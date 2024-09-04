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
notNone = lambda thing: thing != None

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


def next_free(occupied: List[bool], criterion=None, append_to:int=None) -> Optional[int]:
    """
    Looks for the first False value within a list of truth values.

    >>> next_free([1,1,0,1,0,0]) # using ints instead of booleans for brevety
    2

    If no more value is free in list, it can append up to a given value

    >>> next_free([True]*4, append_to=3) # None, nothing free
    >>> next_free([True]*4, append_to=6)
    4

    :arg criterion: Callback which gets the potential value and can decide whether this
      value is fine. Can be used for constraining an acceptable next free lane.
    """
    for idx, val in enumerate(occupied):
        if not val and (criterion(idx) if criterion else True):
            return idx
    return len(occupied) if append_to != None and len(occupied) < append_to else None

## Note on naming:
## "in" is a reserved keyword in python, so all inputs are called a,b,c,... even if there is ony one

Int = namedtuple("Int", ["id", "out", "a"])          #: Integrator, integrates input "a", output to "out"
Mul = namedtuple("Mul", ["id", "out", "a", "b"])     #: Multiplier, multiplies inputs "a" with "b", output to "out"
Id  = namedtuple("Id",  ["id", "out", "a"])          #: Identity element, just passes input "a" to output "out"
Const = namedtuple("Const", ["id", "out" ])          #: Constant giver. output on (cross lane "out")
Out = namedtuple("Out", ["id", "lane"])              #: Front panel output (ACL_OUT) on lane "lane"
Ele = Union[Int,Mul,Const,Id,Out]                    #: type of any kind of element defined so far
isEle = lambda thing: isinstance(thing, get_args(Ele))


class DefaultLUCIDAC:
    """
    This describes a default LUCIDAC REV1 setup with
    
    - M0 = MIntBlock (8 integrators)
    - M1 = MMulBlock (4 multipliers and ID-lanes)
    
    In particular, note that the clanes of M0 and M1 have switched during the
    transition from REV0 to REV1 hardware.
    """
    
    num_int = 8
    num_mul = 4
    num_const = 2 # REV1 has constant givers in U block, this is purely "virtual" here
    num_id  = 4 # REV1 identity elements in MMul block
    num_acls = 8 # REV1 ACL_IN and ACL_OUT ports (each)
    
    MIntOffset = 0       # M0 block
    MMulOffset = num_int # M1 block
    acl_offset = 24 # where the ACL lanes start

    @staticmethod
    def reservoir(default_value=False):
        return {
            Int:   [default_value]*DefaultLUCIDAC.num_int,
            Mul:   [default_value]*DefaultLUCIDAC.num_mul,
            Const: [default_value]*DefaultLUCIDAC.num_const,
            Out:   [default_value]*DefaultLUCIDAC.num_acls,
            Id:    [default_value]*DefaultLUCIDAC.num_id,
        }
    
    @classmethod
    def make(cls, t:Ele, idx):
        """
        A factory for the actual elements.
    
        >>> DefaultLUCIDAC().make(Int, 1)
        Int(id=1, out=1, a=1)
        >>> DefaultLUCIDAC().make(Mul, 3)
        Mul(id=3, out=11, a=14, b=15)
        """
        if t == Int:
            return Int(idx, cls.MIntOffset+idx, cls.MIntOffset+idx)
        if t == Mul:
            return Mul(idx, 
                cls.MMulOffset + idx,
                cls.MMulOffset + 2*idx,
                cls.MMulOffset + 2*idx+1)
        if t == Id:
            # identity elements on Mul-Block map the first 4 MMul inputs on the last 4 MMul outputs
            return Id(idx, cls.MMulOffset+4+idx, cls.MMulOffset+idx)
        if t == Const:
            # Convention for REV1 constants:
            # const(idx=0) => taken from clane 14 => has to be used in lanes  0..15
            # conts(idx=1) => taken from clane 15 => has to be used in lanes 16..31
            return Const(idx, 14 + idx)
        if t == Out:
            return Out(idx, cls.acl_offset + idx)
        
    @staticmethod
    def populated():
        "An unsorted list of all allocatable computing elements"
        return flatten([ [ DefaultLUCIDAC.make(t,i) for i,_ in enumerate(v) ] for t,v in DefaultLUCIDAC.reservoir().items() ])
    
    
    @classmethod
    def resolve_mout(cls, idx, reservoir):
        """
        Simplistic way to map mul block outputs to a reservoir.
        This is sensitive on M0 and M1 block positions.
        """
        if idx < 0:  raise ValueError(f"0 < {idx=} < 16 too small")
        if idx < 8:  return reservoir[Int][idx]
        if idx < 12: return reservoir[Mul][idx - cls.MMulOffset]
        if idx < 16: return reservoir[Id][idx - 12]
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
            raise ValueError(f"Have only {len(self.allocated[t])} Computing Elements of Type {t} available, inexistent id {id} requested.")

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
        # use_constant is a method of the Routing and Circuit classes
        if hasattr(self, "use_constant"):
            self.use_constant()
        return self.alloc(Const, id)
    
    def identity(self, id=None):
        "Allocates one Identity element"
        return self.alloc(Id, id)
    
    # some more fun
    def ints(self, count):
        "Allocate count many integrators"
        return [self.int() for x in range(count)]

    def muls(self, count):
        "Allocate count many multipliers"
        return [self.mul() for x in range(count)]
    
    def identities(self, count):
        "Allocate count many identifiers"
        return [self.identity() for x in range(count)]
    
    def front_output(self, id=None):
        "Allocates an ACL_OUT Front panel output"
        return self.alloc(Out, id)


class Route:
    """
    Routes are the essential building block of this circuit API.
    A list of routes is a way to describe the sparse system matrix (UCI-matrix).
    Sparse matrix values ``A[i,j]`` can be described with lists of 3-tuples
    ``(i,j,A)``, i.e. the position and value. This is what ``(uin,iout,coeff)``
    basically describe. Additionally, there is the ``lane`` which describes the
    internal structure of the UCI matrix. The maximum of 32 lanes corresponds to
    the fact that only 32 elements within the system matrix can be nonzero.

    Python allows for any types for the tuple values. Regularly, instances of
    the computing elements (:class:Int, :class:Mul, etc) are used at the
    ``uin`` and ``iout`` slots.

    This compiler knows the concept of "not yet placed" routes. This are routes
    where ``lane == None``. Some of our codes refer to such routes as "logical"
    in contrast to "physically" placed routes. In this code, unplaced routes are
    called "Connection", i.e. they can be generated with the :func:`Connection`
    function.
    """
    
    #: iout constant in order to not connect.
    do_not_connect = -1
    
    def __init__(self, uin, lane, coeff, iout):
        self.uin = uin
        self.lane = lane
        self.coeff = coeff
        self.iout = iout
    
    def __repr__(self):
        return f"Route(uin={self.uin}, lane={self.lane}, coeff={self.coeff}, iout={self.iout})"

    def __iter__(self):
        yield self.uin
        yield self.lane
        yield self.coeff
        yield self.iout
        
    def __eq__(self, other):
        return list(self) == list(other)

    def resolve(self):
        if isEle(self.uin):
            self.uin = self.uin.out

        if isEle(self.iout):
            if hasattr(self.iout, "b"):
                # element with more then one input
                raise ValueError(f"Please provide input port for {self.iout=} in {self}")
            elif hasattr(self.iout, "a"):
                self.iout = self.iout.a
            else:
                raise ValueError(f"Element has no inputs. Probably mixed up sinks and sources?")
    
    def sanity_list(self):
        errors = []
        if None in self:
            errors.append(f"Route contains None values.")
        if not self.uin in range(0,16):
            errors.append(f"Uin out of range in {self}")
        if not self.lane in range(0,32):
            errors.append(f"Lane out of range in {self}")
        if not (-10 <= self.coeff and self.coeff <= +10):
            errors.append(f"Coefficient out of range in {self}")
        if not self.iout in range(0,32) and self.iout != self.do_not_connect:
            errors.append(f"Iout out of range in {self}")
        return errors
            
    def sanity_raise(self):
        error = ",".join(self.sanity_list())
        if error:
            raise ValueError(error)
        


def Connection(source:Union[Ele,int], target:Union[Ele,int], weight=1):
    """
    Syntactic sugar for a "logical route", i.e. a Route without a lane.        

    >>> r = Reservoir()
    >>> I1, M1 = r.int(), r.mul()
    >>> Connection(M1.a, I1.out)
    Route(uin=8, lane=None, coeff=1, iout=0)
    >>> Connection(M1, I1)
    Route(uin=Mul(id=0, out=8, a=8, b=9), lane=None, coeff=1, iout=Int(id=0, out=0, a=0))

    """
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
        if val < -1 or val > +1:
            raise ValueError(f"Integrator ICs can only be in range [-1,+1], {val} given for element {el}. Consider rescaling your ODE or coefficient upscaling.")
        el = el.id if isinstance(el, Int) else el
        self.ics[el] = val
    
    def set_k0(self, el:Union[Int,int], val:float):
        el = el.id if isinstance(el, Int) else el
        self.k0s[el] = val
    
    def set_k0_slow(self, el:Union[Int,int], val:bool):
        self.set_k0(el, self.slow if val else self.fast)
        
    def generate(self):
        return {
            "elements": [dict(k=k, ic=ic) for k,ic in zip(self.k0s, self.ics)]
        }

    def load(self, config):
        """
        Inverts what :meth:`generate` is doing.
    
        >>> b = MIntBlock()
        >>> b.randomize()
        >>> config = b.generate()
        >>> c = MIntBlock()
        >>> c.load(config) == c # chainable
        True
        >>> assert b.ics == c.ics
        >>> assert b.k0s == c.k0s
        """
        for idx, integrator in enumerate(config["elements"]):
            if "k" in integrator:
                self.k0s[idx] = integrator["k"]
            if "ic" in integrator:
                self.ics[idx] = integrator["ic"]
        return self
    
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
    generates the Output-centric matrix configuration at the end. Most likely,
    as a user you don't want to intiate a Routing instance but a Circuit instance
    instead.
    
    :arg accept_dirty: Flag for allowing to add "dirty" Routes, i.e. illegal Routes,
        without raising at :meth:`add`. Instead, you can use :meth:`sanity_check`
        later to see the problems once more. May be useful for importing existing
        circuits.
    """
    max_lanes = 32
    #routes : List[Route]
        
    def available_lanes(self):
        """
        Returns a list of lane indices generally available in the LUCIDAC (independent of
        their allocation). If you set the class attribute ``lanes_constraint``, their values
        will be used.
    
        >>> r = Routing()
        >>> r.lanes_constraint = [3, 7, 17]
        >>> r.connect(0, 8)
        Route(uin=0, lane=3, coeff=1, iout=8)
        >>> r.connect(3, 7)
        Route(uin=3, lane=7, coeff=1, iout=7)
        >>> r.connect(12, 14)
        Route(uin=12, lane=17, coeff=1, iout=14)
        >>> r.connect(7, 9)
        Traceback (most recent call last):
        ...
        ValueError: All [3, 7, 17] available lanes occupied, no more connections possible.

        """
        # for a fully functional lucidac, do this:
        #return list(range(32))
        # Instead, we know these lanes are working only:
        if hasattr(self, "lanes_constraint"):
            return self.lanes_constraint
        else:
            return list(range(32))
        #return [0,1,2,3,4,5, 14,15, 16,17, 18,19, 20,21, 30,31]
    
    def __repr__(self):
        return f"Routing({pprint.pformat(self.routes)})"
    
    def __init__(self, routes: List[Route] = None, accept_dirty=False, **kwargs):
        super().__init__(**kwargs)  # forwards all unused arguments
        self.routes = []
        self.u_constant = None
        self.accept_dirty = accept_dirty
        if routes:
            self.add(routes)
    
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

    
    def use_constant(self, use_constant=True):
        """
        Activates/Configures the system's constant giver source. A constant giver allows to
        use constant numbers within the computation. A constant then can be connected for
        instance to an integrator or multiplier or summed with other values or constants.
        
        In LUCIDAC, there is one constant source in the U-Block which can configured with
        these values:
    
        * ``True`` or ``1.0`` or ``1``: Generates the constant ``+1``
        * ``0.1`` generates the constant ``+0.1``
        * ``False`` removes the overall constant
        
        Do not use ``None`` for turning off the constant, as this is the default value for
        not passing the constant request at all to the LUCIDAC.
        
        The constant can be further modified by the coefficient in the lane. This allows for
        (up and down) scaling and sign inversion of the constant.
        
        This method only registers the use of the constant. In order to make use of it, routes
        using Constants have to be added. As the constants are only available at certain
        clane/lane positions, you should make use of the :meth:`Reservoir.const` method in
        order to obtain a Constant object and connect it with :meth:`connect`, which will
        figure out a suitable lane.
        """
        self.u_constant = use_constant
    
    def next_free_lane(self, constraint=None):
        """
        Allocates and returns the next free lane in the circuit.
        
        :arg constraint: can be a callback which gets a candidate lane and can accept it as suitable
           or not. This is useful for instance for the constant sources or ACL_IN/OUT features
           which are only available on certain lanes or lane combinations.
        """
        route_for_lane = [ find(lambda r: r.lane == lane, None, self.routes) for lane in self.available_lanes() ]
        is_lane_occupied = [ True if x else False for x in route_for_lane ]
        #print("next_free_lane", self.available_lanes())
        #print("next_free_lane", is_lane_occupied)
        #occupied_lanes = [ r.lane for r in self.routes ]
        idx = next_free(is_lane_occupied, criterion=constraint)#, append_to=self.max_lanes)
        #print("next_free_lane = ",idx)
        if idx == None:
            raise ValueError(f"All {self.available_lanes()} available lanes occupied, no more connections possible." +\
                             ("" if not constraint else " But note that custom constraints were applied!"))
        return self.available_lanes()[idx]
    
    def add(self, route_or_list_of_routes:Union[Route,List[Route]]):
        """
        Main method for adding one or multiple routes to the internal route list.
        
        If a route containing Elements or a Connection (i.e. a Route with ``lane=None``) is given, this function
        will do an "immediate pick and place". So if you want, this is the *compiler* component in this class.
        If a "final" route is given, with only numeric arguments, there is not much to do.
        
        As a matter of principle, this function never *corrects* data it receives. That is, it *does* a 
        certain amount of proof/integrity checking which yields ``ValueErrors`` if we complain about:
        
        - Checking whether a Constant can be routed that way
        - Checking if the requested lane is already in use
        - Checking whether values are out of bounds (i.e. lanes, coefficients, etc)
        
        If you don't want this function to raise on invalid data, set the class attribute ``accept_dirty=True``.
        This option can also be passed to the constructor.
        """
        if isinstance(route_or_list_of_routes, list):
            return list(map(self.add, route_or_list_of_routes))
        
        route = route_or_list_of_routes
        uin, lane, coeff, iout = route
       
        if isinstance(uin, Const):
            right_ublock_chip  = lambda potential_lane: 15 < potential_lane
            left_ublock_chip   = lambda potential_lane: potential_lane < 16
            if lane is None:
                if uin.out == 14:
                    criterion = right_ublock_chip
                elif uin.out == 15:
                    criterion = left_ublock_chip
                else:
                    raise ValueError(f"Unacceptable Constant clane requested in unrouted {route}")
                lane = self.next_free_lane(criterion)
            else:
                if uin.out == 14 and not right_ublock_chip(lane):
                    raise ValueError(f"No Constant available at {route}, lane must be >15")
                if uin.out == 15 and not left_ublock_chip(lane):
                    raise ValueError(f"No Constant available at {route}, lane must be <16")
        
        if isinstance(iout, Out):
            lane = iout.lane
            iout = Route.do_not_connect
        
        if lane is None:
            lane = self.next_free_lane()
        else:
            if lane in [ r.lane for r in self.routes ]:
                raise ValueError(f"Cannot append {route} because this lane is already occupied.")
            
        route = Route(uin, lane, coeff, iout)
        
        # at the end, replace the symbols with numbers.
        route.resolve()
        
        # out of bounds check
        if self.accept_dirty:
            for err in route.sanity_list():
                print(f"Warning at adding Route: {err}")
        else:
            route.sanity_raise()
        
        self.routes.append(route)
        return route

    def connect(self, source:Union[Ele,int], target:Union[Ele,int], weight=1):
        """
        Syntactic sugar for adding a :func:`Connection`.
        :returns: The generated Route.
        """
        return self.add(Connection(source,target,weight))
    
    def route(self, uin, lane, coeff, iout):
        """
        Syntactic sugar for adding a :class:`Route`.
        :returns: The generated Route.
        """
        return self.add(Route(uin, lane, coeff, iout))
   
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
            I=clean([r.iout for r in self.routes if r.lane == lane and r.iout != Route.do_not_connect] for lane in range(32)),
            C=[route.coeff if route else 0 for route in (find(lambda r, lane=lane: r.lane == lane, None, self.routes) for lane in range(32))]
        )
    
    @staticmethod
    def input2output(inmat, keep_arrays=True):
        """
        Input/Output centric format conversion. Relevant only for C block.
        Maps ``Array<int|None,32>`` onto ``Array<Array<int>|int, 16>``.
        
        Example:
        
        >>> iouts_inputs = [ r.iout for r in Routing().randomize(seed=37311).routes ]
        >>> print(iouts_inputs)
        [7, 5, 2, 9, 2, 15, 7, 1, 5, 7, 6, 1, 5, 0, 10, 7, 13, 3, 9, 9, 10, 1, 9, 2, 1, 7, 12, 8, 10, 10, 1, 3]
        >>> Routing.input2output(iouts_inputs) # doctest: +NORMALIZE_WHITESPACE
        [[13],
         [7, 11, 21, 24, 30],
         [2, 4, 23],
         [17, 31],
         [],
         [1, 8, 12],
         [10],
         [0, 6, 9, 15, 25],
         [27],
         [3, 18, 19, 22],
         [14, 20, 28, 29],
         [],
         [26],
         [16],
         [],
         [5]]

        """
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
        """
        Input/Output centric format conversion. Relevant only for C block.
        Maps ``Array<Array<int>|int,16>`` onto ``Array<int|None,32>``.
        
        This is obviously the inverse of ``input2output``:
        
        >>> iouts_inputs  = [ r.iout for r in Routing().randomize(seed=75164).routes ]
        >>> iouts_outputs = Routing.input2output(iouts_inputs)
        >>> again_inputs  = Routing.output2input(iouts_outputs)
        >>> iouts_inputs == again_inputs
        True
        
        :returns: List of size 32.
        """
        input = [ None for _ in range(32) ]
        for clane, lanes in enumerate(outmat):
            if lanes:
                for lane in lanes:
                    input[lane] = clane
        return input
    
    @staticmethod
    def coeff_upscale(c_elements, raise_out_of_bounds=True):
        upscaling = [ (v < -1 or v > 1) for v in c_elements ]
        scaled_c = [ (c/10 if sc else c) for sc, c in zip(upscaling, c_elements) ]
        return upscaling, scaled_c
    
    def sanity_check(self, also_print=True):
        """
        Performs a number of plausibilty and sanity checks on the given circuit. These are:
        
        1. General data type check on the given routes (out of bounds, etc)
        2. For computing elements with more then one input (currently only the multipliers):
           Checks whether no input or all are used.
        
        The sanity check is the last bastion between ill-defined data and a writeout to
        LUCIDAC, which will probably complain in a less comprehensive way.
        
        :returns: A list of human readable messages as strings. Empty list means no warning.
        
        Examples on errnous circuits:
        
        >>> a = Circuit()
        >>> a.routes.append(Route(17, -32, -24.0, None))
        >>> warnings_as_list = a.sanity_check()
        Sanity check warning: Route contains None values.
        Sanity check warning: Uin out of range in Route(uin=17, lane=-32, coeff=-24.0, iout=None)
        Sanity check warning: Lane out of range in Route(uin=17, lane=-32, coeff=-24.0, iout=None)
        Sanity check warning: Coefficient out of range in Route(uin=17, lane=-32, coeff=-24.0, iout=None)
        Sanity check warning: Iout out of range in Route(uin=17, lane=-32, coeff=-24.0, iout=None)
        
        Obviously, in the example above the problem started in the first place because the user
        accessed the ``routes`` atribute instead of using the :meth:`route` or :meth:`add`
        methods, which already do a good part of the checking. In general, never access the
        ``routes`` directly for writing.
        
        The situation is more difficult when at routing time the problem is not detectable but
        later it is:
        
        >>> b = Circuit()
        >>> i = b.int()
        >>> m = b.mul()
        >>> b.connect(i, m.a)
        Route(uin=0, lane=0, coeff=1, iout=8)
        >>> warnigns_as_list = b.sanity_check()
        Sanity check warning: Multiplier 0 (counting from 0) has input but output is not used (clane=8 does not go to some route.uin).
        Sanity check warning: Warning: Multiplier 0 is in use but connection B is empty

        There are a number of mis-uses which this checker cannot detect, by design. This
        is, for example, when inputs and outputs are mixed up:
        
        >>> c = Circuit()
        >>> correct0 = c.connect(i, m.a)
        >>> correct1 = c.connect(i, m.b)
        >>> errnous = c.connect(m.a, i.out)
        >>> c.sanity_check() == []
        True

        The reason for this is because in this example, the explicit member access ``m.a`` or
        ``i.out`` resolves to integers and the checker cannot find out whether the indices where
        given intentionally or by accident.


        """
        warnings = []
        
        ### General route check
        # These are actually not warnings but errors.
        for route in self.routes:
            warnings += route.sanity_list()
        
        ### Multiplier check
        multipliers_used = [False]*DefaultLUCIDAC.num_mul
        multipliers = [ DefaultLUCIDAC.make(Mul, i) for i in range(DefaultLUCIDAC.num_mul) ]

        # first determine which ones have either inputs or outputs connected
        for route in self.routes:
            for m in multipliers:
                if route.uin == m.out or route.iout == m.a or route.iout == m.b:
                    multipliers_used[m.id] = True
                    
        def has_connection(test):
            connected = False
            for route in self.routes:
                if test(route):
                    connected = True
            return connected
        
        # then determine if all ports are connected
        for i,(used, m) in enumerate(zip(multipliers_used, multipliers)):
            if used:
                if not has_connection(lambda route: route.uin == m.out):
                    warnings.append(f"Multiplier {i} (counting from 0) has input but output is not used (clane={m.out} does not go to some route.uin).")
                if not has_connection(lambda route: route.iout == m.a):
                    warnings.append(f"Warning: Multiplier {i} is in use but connection A is empty")
                if not has_connection(lambda route: route.iout == m.b):
                    warnings.append(f"Warning: Multiplier {i} is in use but connection B is empty")

        # TODO should use logging instead
        if also_print:
            for warning in warnings:
                print(f"Sanity check warning: {warning}")

        return warnings

    def generate(self, sanity_check=True):
        """
        Generate the configuration data structure required by the JSON protocol, which is
        that "output-centric configuration". This is a major function of the class. You
        can use the data structure generated here immediately to produce JSON configuration
        files as standalone, for instance by passing the output of this function to
        ``json.dumps(circuit.generate())``.
        
        .. note::
        
           The C-Matrix values here are correctly scaled.
        """
        
        if sanity_check:
            self.sanity_check()
        
        U,C,I = self.routes2input()
        upscaling, scaled_c = self.coeff_upscale(C)
        
        d = {
            "/U": dict(outputs = U),
            "/C": dict(elements = scaled_c),
            "/I": dict(outputs = self.input2output(I), upscaling = upscaling)
        }
        
        # hopefully this also allows to turn OFF the constant by setting it to False...
        if self.u_constant != None:
            d["/U"]["constant"] = self.u_constant
        
        return d
        
    def load(self, cluster_config):
        """
        The inverse of generate. Useful for loading an existing circuit. You can load an
        existing standalone JSON configuration file by using this function.
        
        The following code snippet shows that :meth:`load` and :meth:`generate` are really
        inverse to each other, allowing to first export and then import the same circuit:
        
        >>> a = Routing().randomize()
        >>> b = Routing().load(a.generate(sanity_check=False))
        >>> a.routes == b.routes
        True
        
        .. note::
        
           Also accepts a carrier-level configuration. Does not accept a configuration message
           including the JSON Envelope right now.
        """
        
        if "/0" in cluster_config:
            cluster_config = cluster_config["/0"]
        
        # load all in output centric format
        U = cluster_config["/U"]["outputs"] if "/U" in cluster_config else [ None ]*32
        C = cluster_config["/C"]["elements"] if "/C" in cluster_config else [ 0.0  ]*32
        I = cluster_config["/I"]["outputs"] if "/I" in cluster_config else [ None ]*16
        I = self.output2input(I)
        
        if "upscaling" in cluster_config["/I"]:
            for i in range(32):
                if cluster_config["/I"]["upscaling"][i]:
                    C[i] *= 10
        
        if "constant" in cluster_config["/U"]:
            self.use_constant(cluster_config["/U"]["constant"])
        
        for lane,(u,c,i) in enumerate(zip(U,C,I)):
            if u == None:
                continue
            if i == None or i == []:
                continue
            if not isinstance(i, list):
                i = [i]
            for ii in i:
                self.add(Route(u,lane,c,ii))
        return self
    
    def to_pybrid_cli(self):
        """
        Generate the Pybrid-CLI commands as string out of this Route representation.
        """
        self.sanity_check()
        return "\n".join(f"route -- carrier/0 {r.uin:2d} {r.lane:2d} {r.coeff: 7.3f} {r.iout:2d}" for r in self.routes)
    
    def to_dense_matrix(self, sanity_check=True):
        """
        Generates a dense numpy matrix for the UCI block, i.e. a real-valued 16x16 matrix with
        bounded values [-20,20] where at most 32 entries are non-zero.
        """
        if sanity_check:
            self.sanity_check()
        import numpy as np
        UCI = np.zeros((16,16))
        for (uin, _lane, coeff, iout) in self.routes:
            if iout != Route.do_not_connect:
                UCI[iout,uin] += coeff
        return UCI
    
    def to_dense_matrices(self, sanity_check=True) -> UCI:
        """
        Generates the three matrices U, C, I as dense numpy matrices.
        C and I are properly scaled as in the real system (upscaling happens in I).
        
        :returns: 3-Tuple of numpy matrices for U, C, I, in this order.
        
        Note that one way to reproduce :meth:`to_dense_matrix` is just by
        computing ``I.dot(C.dot(U))`` on the output of this function.
        
        >>> import numpy as np
        >>> c = Circuit().randomize()
        >>> U, C, I = c.to_dense_matrices(sanity_check=False) # skipping for doctesting
        >>> np.all(I.dot(C.dot(U)) == c.to_dense_matrix(sanity_check=False))
        True
        """
        if sanity_check:
            self.sanity_check()
        import numpy as np
        U = np.zeros((32,16))
        C = np.zeros((32,32))
        I = np.zeros((16,32))
        
        for (uin, lane, coeff, iout) in self.routes:
            assert not None in (uin, lane, iout), "Nones behave badly in numpy array subscription. Sanatize your routes."
            U[lane, uin]  = 1
            I[iout, lane] = 1 if abs(coeff) < 10 else 10
            C[lane, lane] = coeff / I[iout, lane]
            if iout == Route.do_not_connect:
                I[iout, lane] = 0
        
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
        self.sanity_check()
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
        Trivially "reverse engineer" a circuit based on routes. Tries to output valid
        python code as string.
        """
        self.sanity_check()
        
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
        self.adc_channels = adc_channels if adc_channels else [None]*8
        
    def set_acl_select(self, acl_select):
        self.acl_select = acl_select
        
    def set_adc_channels(self, adc_channels):
        self.adc_channels = adc_channels

    def measure(self, source:Union[Ele,int], adc_channel=None):
        """
        Syntactic sugar to set an adc_channel.
        """
        if adc_channel == None:
            # TODO is untested
            adc_channel = next_free(map(notNone, self.adc_channels))
        if not adc_channel in range(0,8):
            raise ValueError(f"{adc_channel=} illegal, expecting in 0..7")
        # first have to look for element in routing
        uin = source.out if isEle(source) else source
        self.adc_channels[adc_channel] = uin
        return adc_channel
        
    def generate(self):
        "Returns carrier configuration, not cluster configuration"
        ret = {}
        if self.acl_select:
            #if not all(isinstance(v, bool) for v in self.acl_select):
            #    raise ValueError(f"Unsuitable ACL selects, expected list of bools: {self.acl_select}")
            ret["acl_select"] = self.acl_select
        if len(list(filter(notNone, self.adc_channels))):
            # TODO: Probably check again with the Nones.
            if not all(isinstance(v, int) or v == None for v in self.adc_channels):
                raise ValueError(f"Unsuitable ADC channels, expected list of ints: {self.adc_channels}")
            ret["adc_channels"] = self.adc_channels
        return ret
    
    def load(self, config):
        if "acl_select" in config:
            self.acl_select = config["acl_select"]
        if "adc_channels" in config:
            self.adc_channels = config["adc_channels"]
        return self

class Circuit(Reservoir, MIntBlock, Routing, Probes):
    """
    The Circuit class collects all reconfigurable properties of a LUCIDAC. The class joins
    all features from it's parents in a *mixin idiom*. (This means that, if you really want to,
    you also can use the individual features on its own. But there should be no need to do so)
        
    This class provides, for instance, an improved version of the 
    :meth:`Reservoir.int` method which also sets the integrator state (initial value and time factors)
    in one method call.

    Most of all, this function generates the final configuration format required for LUCIDAC.
    
    However, the mixin idiom also has it's limitations. For instance, for the ``Reservoir``, there
    will be no "backwards syncing", i.e. if routes are
    added manually without using the Reservoir, it's bookkeeping is no more working. Example:
        
    >>> circ = Circuit()
    >>> circ.connect(0, 0) # defacto connects M0 first output to M0 first input
    Route(uin=0, lane=0, coeff=1, iout=0)
    >>> I = circ.int()
    >>> print(I)
    Int(id=0, out=0, a=0)
    >>> circ.connect(I, I)
    Route(uin=0, lane=1, coeff=1, iout=0)

    One could expect in this example that ``circ.int()`` hands out the second integrator (``id=1``)
    but it does not. The registry only knows about how often it was called and does not know at
    all how the computing elements are used in the Routing.
    """
    
    def __init__(self, routes: List[Route] = [], accept_dirty=False):
        super().__init__(routes=routes, accept_dirty=accept_dirty)
    
    def int(self, *, id=None, ic=0, slow=False):
        "Allocate an Integrator and set it's initial conditions and k0 factor at the same time."
        el = Reservoir.int(self, id)
        self.set_ic(el, ic)
        self.set_k0(el, MIntBlock.slow if slow else MIntBlock.fast)
        return el
    
    def probe(self, source:Union[Ele,int], front_port=None):
        """
        Syntactic sugar to route a port to the front panel output.
        The name indicates that an oscilloscope probe shall be connected
        to this port.
        If no port is given, will count up.
        
        If you need a weight, use :meth:`connect` directly as in
        ``circuit.connect(source, circuit.front_output(front_port), weight=1.23)``.
       
        :arg front_output: Integer describing the front port number (0..7)
        :returns: The generated Route (is also added)
        
        See also :meth:`Circuit.measure` for putting a singal to ADC/DAQ.
        """
        target = self.alloc(Out, front_port) # None passes to default alloc None!
        return self.add(Connection(source, target))
    
    def load(self, config_message):
        """
        Loads the configuration which :meth:`generate` spills out. The full circle.
        """
        config_carrier = config_message["config"] if "config" in config_message else config_message
        Probes.load(self, config_carrier)
        config_cluster = config_carrier["/0"] if "/0" in config_carrier else config_carrier
        
        if "/M0" in config_cluster:
            MIntBlock.load(self, config_cluster["/M0"])
        Routing.load(self, config_cluster)

        return self
    
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
    
    def generate(self, skip=None, sanity_check=True):
        """
        Returns the data structure required by the LUCIDAC set_config call *for a given carrier*,
        not cluster. The output of this function can be straightforwardly fed into ``LUCIDAC.set_circuit``.
        
        The LUCIDAC cluster is always part of the carrier level configuration:
        
        >>> "/0" in Circuit().randomize().generate(sanity_check=False)
        True
        
        :arg skip: An entity (within LUCIDAC) to skip, for instance "/M1"
        :arg sanity_check: Whether to carry out a sanity check (results in printouts)
        """
        cluster_config = Routing.generate(self, sanity_check=sanity_check)
        cluster_config["/M0"] = MIntBlock.generate(self) 
        cluster_config["/M1"] = {} # MMulBlock
        
        if skip:
            cluster_config = { k:v for k,v in cluster_config.items() if not skip in k }

        carrier_config = {}
        carrier_config["/0"] = cluster_config
        carrier_config.update(Probes.generate(self).items())

        return carrier_config
        
    def write(self, hc, **args):
        "Shorthand to write out configuration to hybrid controller"
        hc.set_circuit(self.generate(**args))

    def to_json(self, **args):
        "Shorthand to get JSON. Typically you don't need this"
        import json
        config = self.generate(**args)
        return json.dumps(config)
        
    def to_ascii_art(self, full_Cblock=False):
        """
        Creates an "ASCII art" of the LUCIDAC including the current configuration.
        
        Includes: U, C, I, Mblock configuration
        
        Does not yet include:
        
        - ACL IN/OUT
        - Constant givers
      
        """
        
        # The implementation/code for this method stems from the C libsim and thus may look
        # a bit awkward in python.
        
        import numpy as np
        U, C, I = self.to_dense_matrices()
        U = U.T
            
        dump = "LuciPy LUCIDAC ASCII Dump      +--[ UBlock ]----------------------+\n" + \
               "+-[ M0 = MIntBlock ]-----+     | 0123456789abcdef0123456789abcdef |\n"
            
        for i in range(8):
            log10k0 = np.log10(self.k0s[i])
            assert log10k0 == int(log10k0)
            dump += "| INT%ld IC=%+.2f  k0=10^%d |" % (i, self.ics[i], log10k0);
            u_clane_used = np.any(U[i,:])
            c = "A" if i in self.adc_channels else ("-" if u_clane_used else ".")
            dump += f" -{c}> " if u_clane_used else f"  {c}  "
            dump += "%lX " % i
            
            # U Block upper
            dump += "".join("X" if U[i,j] else "." for j in range(32))
            
            dump += " %lX\n" % i
            
        dump += "+-[ M1 =  MulBlock ]-----+\n"
            
        for i in range(8):
            muli, ab = "MUL%ld" % (i/2), "a" if i%2==0 else "b"
            if i < 4:
                dump += "| %s.%s        MUL%ld.out |" % (muli, ab, i)
            else:
                dump += "| %s.%s                 |" % (muli, ab)
            
            # U Block lower
            u_clane_used = np.any(U[i+8,:])
            c = "A" if i in self.adc_channels else ("-" if u_clane_used else ".")
            dump += f" -{c}> " if u_clane_used else f"  {c}  "
            dump += "%lX " % (i+8)
            dump += "".join("X" if U[i+8,j] else "." for j in range(32))
            dump += " %lX\n" % (i+8)

        Uout1 = "".join("v" if np.any(U[:,j]) else "-" for j in range(32))
        #Uout2 = "".join("v" if np.any(U[:,j]) else "" for j in range(32))

        dump += f"+------------------------+     +-{Uout1}-+\n";
        #dump += f"                                  {Uout2}\n";
        dump += "\n"
        
        dump += "                               +--[ CBlock ]----------------------+\n" + \
                "                               | 0123456789abcdef0123456789abcdef |\n"
            
        # Dumping the c block (up to 80 chars width)
        Cwhite = " "*34 # place of M blocks
        dump += Cwhite + "\n"
        #dump += "".join("v" if C[i,i] else " " for i in range(32))

        for i in range(32):
            factor = C[i,i]
            if not full_Cblock and factor == 0:
                continue
            dump += Cwhite
            dump += "".join(("X" if j==i else ("|" if np.diag(C)[j]!=0 else ".")) if factor else "." for j in range(32) )
            dump += " C%02ld = %+02.3f " % (i, factor)
            dump += "\n"
            
        dump += Cwhite
        dump += " "*32; # cblock->factor[i] ? "|" : " ";
        dump += "\n" #dump += "+--------------+\n"
            
            
        dump += "                               +--[ IBlock ]----------------------+\n" + \
                "+-[ M0 = MIntBlock ]-----+     | 0123456789abcdef0123456789abcdef |\n"
            
        for i in range(8):
            # M0 block
            dump += "|                   INT%ld |" % i
            dump += " <-- " if np.any(I[i,:]) else "  .  "
            dump += "%lX " % i
            
            # I block upper
            dump += "".join("X" if I[i,j] else "." for j in range(32))
            dump += " %lX\n" % i
            
        dump += "+-[ M1 =  MulBlock ]-----+\n"
            
        for i in range(8):
            # M1 block
            muli, ab = "MUL%ld" % (i/2),  "a" if i%2==0 else "b"
            dump += "|                 %s.%s |" % (muli, ab)

            # I Block lower
            dump += " <-- " if np.any(I[i+8,:]) else "  .  "
            dump += "%lX " % (i+8)
            dump += "".join("X" if I[i+8,j] else "." for j in range(32))
            dump += " %lX\n" % (i+8)
        
        dump += "+------------------------+     +----------------------------------+\n"

        return dump
    
        
    def to_pybrid_cli(self):
        "Pybrid code generation including both the MIntBlock and Routing."
        nl = "\n"
        ret = "set-alias * carrier" + nl*2
        ret += MIntBlock.to_pybrid_cli(self) + nl
        
        ret += Routing.to_pybrid_cli(self) + nl
        
        ret += "# run --op-time 500000" + nl
        return ret
