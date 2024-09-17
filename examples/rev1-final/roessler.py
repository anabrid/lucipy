#
# Roessler attractor on LUCIDAC,
# part of the guidebook
#
# x' = -0.8y - 2.3z
# y' = 1.25x + 0.2y
# z' = 0.005 + 15z(x - 0.3796)
#

from lucipy import Circuit, Simulation, LUCIDAC, Route
from time import sleep
from lucipy.synchc import RemoteError

r = Circuit()                           # Create a circuit

x     = r.int(ic = .066)
my    = r.int()
mz    = r.int()
prod  = r.mul(id=1)
const = r.const(1)

r.connect(my,    x, weight = -0.8)
r.connect(mz,    x, weight = -2.3)

r.connect(x,     my, weight = 1.25)
r.connect(my,    my, weight = -0.2)

r.connect(const, mz, weight = 0.005)
r.connect(prod,  mz, weight = 10)
r.connect(prod,  mz, weight = 5)

r.connect(mz,    prod.a, weight = -1)
r.connect(x,     prod.b)
r.connect(const, prod.b, weight = -0.3796)

r.probe(x,  front_port=0)
r.probe(my, front_port=1)

hc = LUCIDAC()
hc.set_config(r)

hc.manual_mode("ic")
sleep(0.5)
hc.manual_mode("op")
