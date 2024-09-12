# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

from lucipy.circuits import Int, Mul

a = 1.0
b = 2.8
c = 2.666 / 10

l = Circuit()                           # Create a circuit

mx = l.int(ic = 0.1)
my = l.int()
mz = l.int()
xz = l.mul(1)
xy = l.mul(2)

l.connect(mx, xz.a)                     # Product -x * -z = xz
l.connect(mz, xz.b)

l.connect(mx, xy.a)                     # Product -x * -y = xy
l.connect(my, xy.b)

l.connect(my, mx, weight = -a)
l.connect(mx, mx, weight = a)

l.connect(mx, my, weight = -b)
l.connect(xz, my, weight = -5)
l.connect(my, my, weight = 0.1)

l.connect(xy, mz, weight = 5)
l.connect(mz, mz, weight = c)

l.probe(mx, front_port=4)
l.probe(my, front_port=5)
l.probe(mz, front_port=6)

hc = LUCIDAC()

hc.reset_circuit()

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

conf = l.generate()

# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
conf["/0"]["/M1"]["calibration"] = {
    "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
    "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
    "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}


hc.set_circuit(conf)

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")


