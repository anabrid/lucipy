from lucipy import Circuit, Simulation, LUCIDAC, Route
from lucipy.circuits import Mul
import matplotlib.pyplot as plt
import numpy as np
from time import sleep

#
# Sprott attractor on REV1 Hardware
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

sprott.connect(mx, mxy.a)                   # -xy
sprott.connect(my, mxy.b, weight = -1)

sprott.connect(my, yz.a)                    # yz
sprott.connect(mz, yz.b)

sprott.probe(mx, front_port=6)
sprott.probe(my, front_port=7)

sprott.measure(mx)
sprott.measure(my)

hc = LUCIDAC()

hc.reset_circuit()

config = sprott.generate()

print(config)

hc.set_config(config)

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
    hc.set_op_time(sec=3)

    run = hc.start_run()

    from pylab import *
    x, y = array(run.data()).T

    figure()
    scatter(x,y)
    show()

