from collections import namedtuple
from typing import get_args

Int = namedtuple("Int", ["id", "out", "a"])
Mul = namedtuple("Mul", ["id", "out", "a", "b"])
Ele = Int|Mul

Route = namedtuple("Route", ["uin", "lane", "coeff", "iout"])

def Connection(source:Ele|int, target:Ele|int, weight=1):
    """
    Transforms an argument list somewhat similar to a "logical route" in the
    lucicon code to a physical route.
    """
    if isinstance(source, get_args(Ele)):
        source = source.out
    if isinstance(target, get_args(Ele)):
        # this should spill out an error if the Ele has more then one inputs
        target = target.a
    return Route(source, None, weight, target)

class AnalogReservoir:
    entities # available M1/M2 blocks
    spent : list[CompEl] = [] # allocated types
    
    def __init__(luci_or_entities_or_default=None):
        if isinstance(luci_or_entities_or_default, LUCIDAC):
            luci = luci_or_entities_or_default
            self.entities = luci.get_entities()
        elif luci_or_entities_or_default == None;
            # set to default LUCIDAC config, i.e. M1=MBlockInt, M0=MMulBlock or similar
            pass
        else:
            self.entities = luci_or_entities_or_default
        # todo: better parse entities here, don't save all of them
    
    routes : list[Route]
    def next_free_lane(self):
        # check routes for next free lane
        pass

    def alloc(self, type:CompEl, id=None):
        pass

    def int(self, id=None): self.alloc(Int, id)
    def mul(self, id=None): self.alloc(Mul, id)
    
    def add(route:Route):
        if route.lane == None:
            physical = Route(route.uin, self.next_free_lane(), route.coeff, route.iout)
        else:
            # check if requested lane is free!
            pass
        self.routes.append(physical)
        return physical

    def connect(source:Ele|int, target:Ele|int, weight=1):
        self.add(Connection(source,target,weight))


# Usage is like:


luci = LUCIDAC()

# knows what is available in terms of computing elements
entities = luci.get_entities() # will be fast on second call

alloc = AnalogReservoir(luci or elements or /* assumes default LUCIDAC M1+M2 */)


I1 = alloc.int() # allocates an integrator
M1 = alloc.mul(2) # allocates multiplier 2

# returns Route(I1.out, laneidx++, coeff=10, M1.a)
problem1.connect(I1, M1.a, weight=10)

# Alternative:
problem = [
    Connection(I1, I2),
    Connection(I1, M1.a, 2.0)
]

problem1.configure(hc)


# Usage like:
