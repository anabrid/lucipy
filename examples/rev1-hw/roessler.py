#
# Roessler attractor on LUCIDAC:
#
# x' = -0.8y - 2.3z
# y' = 1.25x + 0.2y
# z' = 0.005 + 15z(x - 0.3796)
#

from lucipy import Circuit, Simulation, LUCIDAC, Route
from time import sleep

r = Circuit()                           # Create a circuit

x     = r.int(ic = .066)
my    = r.int()
mz    = r.int()
prod  = r.mul()
const = r.const(1)

# TODO: Cannot use r.const(0) on this list of usable
#       lanes because Routing.next_free_lane does not properly
#       hand over the list of available lanes but works on
#       naive indices, without the mapping.

#r.lanes_constraint = [ 1, 2, 3, 5, 6, 10, 11, 12, 14 ]
#r.lanes_constraint.append(17) # for the constant

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

r.probe(x, front_port=6)
r.probe(my, front_port=7)

r.measure(x)
r.measure(my)

hc = LUCIDAC()

hc.reset_circuit()

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k: v for k,v in r.generate().items() if not "/M1" in k }

print(config)

hc.set_config(config)

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_daq(num_channels=2)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=100_500_000, no_streaming=True)

    from pylab import *
    x, y = array(hc.start_run().data()).T
    
    plot(x)
    plot(y)
    show()
