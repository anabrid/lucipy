# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

from lucipy.circuits import Int, Mul

l = Circuit()

mx    = l.int(ic = 1)
my    = l.int()
mz    = l.int()
xy    = l.mul()
mxs   = l.mul()
const = l.const()

l.connect(mx, mx)
l.connect(my, mx, weight = -1.8)

l.connect(mx, xy.a)
l.connect(my, xy.b)

l.connect(xy, mz, weight = 1.5)
l.connect(mz, mz, weight = 0.15) #0.2667)

l.connect(mx,    mxs.a)
l.connect(mz,    mxs.b, weight = -2.68)
l.connect(const, mxs.b, weight = -1)

l.connect(mxs, my, weight = 1.536)
l.connect(my,  my, weight = 0.1)

l.probe(mx, front_port=5)
l.probe(my, front_port=6)
l.probe(mz, front_port=7)

hc = LUCIDAC()

hc.reset_circuit()
hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

conf = l.generate()

conf["/0"]["/M1"]["calibration"] = {
    "offset_x": [0.1, 0.05, 0.05, 0.04],
    "offset_y": [0.05, 0, 0, 0],
    "offset_z": [-0.035, -0.027, -0.029, -0.030]
}

hc.set_circuit(conf)

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")


