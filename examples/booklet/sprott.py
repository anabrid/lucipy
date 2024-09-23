from lucipy import Circuit, LUCIDAC
from time import sleep

#
# Sprott attractor on LUCIDAC
# Part of the booklet
#

sprott = Circuit()

mx      = sprott.int(ic = .1)
my      = sprott.int()
mz      = sprott.int()
mxy     = sprott.mul()
yz      = sprott.mul()
const   = sprott.const()

sprott.connect(yz, mx, weight = 10)         # x' = yz

sprott.connect(mx, my, weight = -1)         # y' = x - y
sprott.connect(my, my)
sprott.connect(const, mz, weight = 0.1)     # z' = 1 - xy (scaled!)

sprott.connect(mxy, mz, weight = 10)

sprott.connect(mx, mxy.a,)                  # -xy
sprott.connect(my, mxy.b, weight = -1)

sprott.connect(my, yz.a)                    # yz
sprott.connect(mz, yz.b)

sprott.probe(mx, front_port=0)
sprott.probe(my, front_port=1)
sprott.probe(mz, front_port=2)

hc = LUCIDAC()
hc.set_circuit(sprott)

hc.manual_mode("ic")
sleep(0.5)
hc.manual_mode("op")
