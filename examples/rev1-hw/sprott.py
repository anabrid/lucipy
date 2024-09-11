from lucipy import Circuit, Simulation, LUCIDAC, Route
from lucipy.circuits import Mul
import matplotlib.pyplot as plt
import numpy as np
from time import sleep

#
# Sprott attractor on REV1 Hardware
#


sprott = Circuit()

# andere Lane-Auswahl
#sprott.lanes_constraint = list(range(0,32))[::-1]

# the known defect channel
#sprott.lanes_constraint.remove(27)

#print(sprott.lanes_constraint)

if True:
    scale = 1

    mx      = sprott.int(ic = .1 * scale)
    my      = sprott.int()
    mz      = sprott.int()
    mxy     = sprott.mul()
    yz      = sprott.mul()
    const   = sprott.const()
    
    # FFM
    sprott.probe(mx, front_port=5)
    sprott.probe(my, front_port=6)
    sprott.probe(mz, front_port=7)
    
    # ULM:
    #sprott.probe(mx, front_port=0)
    #sprott.probe(my, front_port=1)
    #sprott.probe(mz, front_port=2)

    sprott.connect(yz, mx, weight = 10*scale)         # x' = yz

    sprott.connect(mx, my, weight = -1*scale)         # y' = x - y
    sprott.connect(my, my, weight=scale)
    sprott.connect(const, mz, weight = 0.1*scale)     # z' = 1 - xy (scaled!)

    sprott.connect(mxy, mz, weight = 10*scale)

    sprott.connect(mx, mxy.a, weight=scale)                   # -xy
    sprott.connect(my, mxy.b, weight = -1*scale)

    sprott.connect(my, yz.a, weight=scale)                    # yz
    sprott.connect(mz, yz.b, weight=scale)
    
else:
    mx      = sprott.int(ic = .01)
    my      = sprott.int()
    mz      = sprott.int()
    mxy    = sprott.mul()
    yz    = sprott.mul()
    const  = sprott.const()

    sprott.connect(yz, mx, weight = 1)         # x' = yz

    sprott.connect(mx, my, weight = -1)         # y' = x - y
    sprott.connect(my, my) 

    sprott.connect(const, mz, weight = 0.01)     # z' = 1 - xy (scaled!)
    sprott.connect(mxy, mz, weight = 1)

    sprott.connect(mx, mxy.a, weight = 10)                   # -xy
    sprott.connect(my, mxy.b, weight = -10)

    sprott.connect(my, yz.a, weight = 10)                    # yz
    sprott.connect(mz, yz.b, weight = 10)



#sprott.measure(mx)
#sprott.measure(my)
#sprott.measure(mz)

hc = LUCIDAC()

print(hc.get_entities())

hc.reset_circuit(dict(keep_calibration=False))
#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})


config = sprott.generate()

if False:
    # These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
    config["/0"]["/M1"]["calibration"] = {
        "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
        "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
        "offset_z": [-0.038, -0.033, -0.0317, -0.033]
    }

config["/0"]["/M1"]["calibration"] = {
        "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
        "offset_y": [ 0.0,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
        "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}

print(config)

hc.set_circuit(
    config,
#    calibrate_offset = True,
#    calibrate_routes = True,
    #calibrate_mblock = False,
)

print(hc.get_circuit())

manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
    hc.set_op_time(us=100)#ms=30)

    run = hc.start_run()

    from pylab import *
    x, y, z = array(run.data()).T

    figure()
    title("z,x")
    scatter(z,x)
    plot(z,x,"-")
    show()

