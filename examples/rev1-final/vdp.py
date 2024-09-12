#
# Van der Pol oscillator
#

from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

eta = 4

vdp = Circuit()

mdy = vdp.int()#ic = 0.01) # TEST
y   = vdp.int(ic = 0.1)
y2  = vdp.mul()
fb  = vdp.mul(2)
c   = vdp.const()

vdp.connect(fb, mdy, weight = -eta)
vdp.connect(y,  mdy, weight = -0.5)
#vdp.connect(c,  mdy, weight = +0.1) # HAVE TO ADD THIS

vdp.connect(mdy, y, weight = 2)

vdp.connect(y, y2.a)
vdp.connect(y, y2.b)

vdp.connect(y2,  fb.a, weight = -1)
vdp.connect(c,   fb.a, weight = 0.25)
vdp.connect(mdy, fb.b)

vdp.probe(mdy, front_port=4)
vdp.probe(y,   front_port=5)

vdp.measure(mdy)
vdp.measure(y)

print(vdp)

hc = LUCIDAC()
hc.sock.sock.debug_print = True
hc.reset_circuit(dict(keep_calibration=False))

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

#hc.set_by_path(["0", "SH"], {"state": "TRACK_AT_IC"})

config = vdp.generate()
# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
config["/0"]["/M1"]["calibration"] = {
    "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
    "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
    "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}

import json

print(json.dumps(config))

# ALL values upscaled
#config["/0"]["/I"]["upscaling"] = [True]*32

hc.one_shot_daq() # this initializes the daq

hc.set_circuit(config)


hc.manual_mode("ic")
from time import sleep
sleep(0.3)
hc.manual_mode("op")
