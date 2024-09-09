#
# Hyperchaotic system, including a quartic term.
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

hc = Circuit()                          # Create a circuit

mw   = hc.int(ic = .01)
z    = hc.int()
my   = hc.int()
x    = hc.int()
x2   = hc.mul()
x4   = hc.mul()
mwx4 = hc.mul()

hc.connect(mwx4, mw, weight = 1.6)
hc.connect(x,    mw, weight = -0.02)
hc.connect(my,   mw, weight = 0.03)
hc.connect(z,    mw, weight = -0.175)

hc.connect(mw, z, weight = 0.2)

hc.connect(z, my, weight = 0.1666)

hc.connect(my, x, weight = 0.15)

hc.connect(x, x2.a)
hc.connect(x, x2.b)

hc.connect(x2, x4.a)
hc.connect(x2, x4.b)

hc.connect(x4, mwx4.a)
hc.connect(mw, mwx4.b)

hc.probe(mw, front_port=5)
hc.probe(x, front_port=6)
hc.probe(z, front_port=7)

config = hc.generate()

hc = LUCIDAC()

hc.reset_circuit(dict(keep_calibration=False))

hc.set_circuit(
    config,
)

hc.manual_mode("ic")
from time import sleep
sleep(0.5)
hc.manual_mode("op")

#mw_out, z_out, my_out, x_out = result.y[mw.id], result.y[z.id], result.y[my.id], result.y[x.id]
#plt.plot(x_out, mw_out)                # Create a phase space plot.

