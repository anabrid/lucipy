from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

e = Circuit()                           # Create a circuit

ramp  = e.int(ic = 1)                   # Integrator for a time linear ramp
const = e.const()                       # Constant for the time linear ramp

scm0  = e.mul()                         # These two multipliers and two
scm1  = e.mul()                         # integrators generate a sine/cosine
sci0  = e.int(ic = 1)                   # with time varying frequency (see 
sci1  = e.int()                         # below).

x     = e.int(ic = 0.65)                # Integrators for x and
y     = e.int(ic = 0.65)                # y component of the spiral

e.connect(const, ramp, weight = -0.1)   # Integrate over a constant

e.connect(ramp, scm0.a)                 # Generate a sine/cosine pair
e.connect(ramp, scm1.a)                 # with varying frequency
e.connect(scm0, sci0, weight = 10)
e.connect(sci0, scm1.b)
e.connect(scm1, sci1, weight = -10)
e.connect(sci1, scm0.b)

e.connect(sci0, x, weight = 0.6)        # Compute the parameterized Euler
e.connect(sci1, y, weight = 0.6)        # spiral.

e.probe(x, front_port=5)
e.probe(y, front_port=6)

print(e)

hc = LUCIDAC()

hc.set_circuit( e.generate() )

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")

