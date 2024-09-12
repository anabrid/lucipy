 #
# Mathieu's differential equation
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

# These are the two parameters of Mathieu's equation which have to 
# be varied to get a stability map. 0 <= a <= 8 and 0 <= q <= 5.
a = 4
q = 1.8

# First we need an amplitude stabilised cosine signal. Since we do not have
# limiters at the moment, we use a van der Pol-oscillator for that purpose.
eta = .1                # A small value ensures good spectral cleanliness

m = Circuit()

mdy = m.int()
y   = m.int(ic = -1)
y2  = m.mul()
fb  = m.mul()
c   = m.const()

m.connect(fb, mdy, weight = -eta * 2)   # We need cos(2t), so all inputs 
m.connect(y,  mdy, weight = -0.5 * 2)   # to the integrators get a factor 2.

m.connect(mdy, y, weight = 2 * 2)

m.connect(y, y2.a)
m.connect(y, y2.b)

m.connect(y2,  fb.a, weight = -1)
m.connect(c,   fb.a, weight = 0.25)
m.connect(mdy, fb.b)

# Now for the actual Mathieu equation:
mdym = m.int()
ym   = m.int(ic = 0.1)
p    = m.mul()

m.connect(ym, mdym, weight = -a)
m.connect(p,  mdym, weight = q)

m.connect(mdym, ym)

m.connect(y, p.a)
m.connect(ym, p.b, weight = 2)


m.probe(ym, front_port=4)


hc = LUCIDAC()
hc.sock.sock.debug_print = True
hc.reset_circuit(dict(keep_calibration=False))

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

#hc.set_by_path(["0", "SH"], {"state": "TRACK_AT_IC"})

config = m.generate()
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
