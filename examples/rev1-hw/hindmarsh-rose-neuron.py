#
# Hindmarsh-Rose model of neural bursting and spiking (see
# https://analogparadigm.com/downloads/alpaca_28.pdf for details).
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

hr = Circuit()                          # Create a circuit

mx  = hr.int(ic = 1)
y   = hr.int(ic = 1)
mz  = hr.int(slow = True, ic = -1)
x2  = hr.mul(1)
mx3 = hr.mul(2)
c   = hr.const()

hr.connect(c,   mx)
hr.connect(mx3, mx, weight = 4)
hr.connect(x2,  mx, weight = 6)
hr.connect(y,   mx, weight = 7.5)
hr.connect(mz,  mx)

hr.connect(mx, mx3.a)
hr.connect(x2, mx3.b)

hr.connect(mx, x2.a)
hr.connect(mx, x2.b)

hr.connect(x2, y, weight = 1.333)
hr.connect(c,  y, weight = -0.066)
hr.connect(y,  y)

hr.connect(mx, mz, weight = -0.4)
hr.connect(c,  mz, weight = 0.32)
hr.connect(mz, mz, weight = 0.1)

hr.probe(mx, front_port=5, weight=-1)
hr.probe(y,  front_port=6)
hr.probe(mz, front_port=7, weight=-1)

hc = LUCIDAC()

hc.reset_circuit()
#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

conf = hr.generate()

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

