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
    const   = sprott.const(1)
    
    # FFM
    sprott.probe(mx, front_port=0)
    sprott.probe(my, front_port=1)
    sprott.probe(mz, front_port=2)
    
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



sprott.measure(mx)
sprott.measure(my)
sprott.measure(mz)

hc = LUCIDAC()

hc.reset_circuit(dict(keep_calibration=False))
#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})


config = sprott.generate()

# S/N 0 device
if False:
    config["/0"]["/M1"]["calibration"] = {
        "offset_x": [ -0.002, -0.002 ,  -0.0015, -0.005  ], # !!! offset_x = input B !!!
        "offset_y": [ +0.002,  0.0015,   0.0035,  0.0    ], # !!! offset_y = input A !!!
        "offset_z": [ -0.026, -0.027 ,  -0.028 , -0.0325 ],
        
        "write_eeprom": True
    }
    hc.circuit_options.mul_calib_kludge = False
elif False:
    config["/0"]["/M1"] = {
        "read_calibration_from_eeprom": True
    }
    hc.circuit_options.mul_calib_kludge = False
else:
    pass

print(config)

hc.set_circuit(
    config,
#    calibrate_offset = True,
#    calibrate_routes = True,
    #calibrate_mblock = True,
)

print(hc.get_circuit())

manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_run(halt_on_overload=False, ic_time=200_000) #, no_streaming=True
    hc.set_op_time(us=100)#ms=30)

    run = hc.start_run()

    from pylab import *
    x, y, z = array(run.data()).T

    figure()
    title("z,x")
    scatter(z,x)
    plot(z,x,"-")
    show()

