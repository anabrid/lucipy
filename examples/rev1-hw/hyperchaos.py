#
# Hyperchaotic system, including a quartic term.
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

hc = Circuit()                          # Create a circuit

fs = False

mw   = hc.int(slow = fs, ic = .01)
z    = hc.int(slow = fs)
my   = hc.int(slow = fs)
x    = hc.int(slow = fs)
x2   = hc.mul()
x4   = hc.mul()
mwx4 = hc.mul()

hc.connect(mwx4, mw, weight = 0.8)
hc.connect(x,    mw, weight = -0.02)
hc.connect(my,   mw, weight = 0.03)
hc.connect(z,    mw, weight = -0.175)

hc.connect(mw, z, weight = 0.2)

hc.connect(z, my, weight = 0.1666)

hc.connect(my, x, weight = 0.15)
hc.connect(x,  x, weight = 0.007)

hc.connect(x, x2.a, weight = 2)
hc.connect(x, x2.b, weight = 2)

hc.connect(x2, x4.a)
hc.connect(x2, x4.b)

hc.connect(x4, mwx4.a)
hc.connect(mw, mwx4.b, weight = 2)

hc.probe(mw, front_port=4)
hc.probe(x, front_port=5)
hc.probe(my, front_port=6)
hc.probe(z, front_port=7)

config = hc.generate()

# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
config["/0"]["/M1"]["calibration"] = {
    "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
    "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
    "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}

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

