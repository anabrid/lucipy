#!/usr/bin/env python

from lucipy import *

circuit = Circuit()

m = circuit.mul(2)
sin = 27 # external input, ACL_IN[3]

# note that the ACL_in weights have no meaning
# since the ACL_IN comes after the c-block

circuit.route(m, sin, 1.0, m.b)
#circuit.connect(sin, m.b, weight=1)

#circuit.connect(circuit.const(), m.b)

#circuit.measure(m)
#circuit.measure(m1)
#circuit.measure(m2)

circuit.probe(m, front_port=0)
#circuit.probe(m, front_port=6)
#circuit.probe(m, front_port=7)

hc = LUCIDAC()
hc.reset_circuit(dict(keep_kalibration=False))

#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

config = circuit.generate()

config["acl_select"] = ["external"]*8

# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
config["/0"]["/M1"]["calibration"] = {
    "offset_x": [ -0.002, -0.002 ,  -0.0015, -0.005  ], # !!! offset_x = input B !!!
    "offset_y": [ +0.002,  0.0015,   0.0035,  0.0    ], # !!! offset_y = input A !!!
    "offset_z": [ -0.026, -0.027 ,  -0.028 , -0.0325 ]
}

print(config)


hc.set_config(config)

measurements = hc.one_shot_daq()
print(measurements)
