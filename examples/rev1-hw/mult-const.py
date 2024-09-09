#!/usr/bin/env python

from lucipy import *

circuit = Circuit()

m0, m1, m2, m3 = circuit.muls(4)
const = circuit.const()

# 0*0: Empty inputs
circuit.connect(const, m0.a, weight=0)
circuit.connect(const, m0.b, weight=0)

# 0*1
circuit.connect(const, m1.a, weight=0)
circuit.connect(const, m1.b, weight=0)

# 0*(-1)
circuit.connect(const, m2.a, weight=0)
circuit.connect(const, m2.b, weight=0)


circuit.measure(m0)
circuit.measure(m1)
circuit.measure(m2)

circuit.probe(m0, front_port=5)
circuit.probe(m1, front_port=6)
circuit.probe(m3, front_port=7)

hc = LUCIDAC()
hc.reset_circuit()

#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

config = circuit.generate()

config["/0"]["/M1"]["calibration"] = {
    "offset_x": [0.0, 0, 0, 0],
    "offset_y": [0.0, 0, 0, 0],
    "offset_z": [-0.035, -0.027, -0.029, -0.030]
}
hc.set_config(config)

measurements = hc.one_shot_daq()
print(measurements)
