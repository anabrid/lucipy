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

vdp.probe(mdy, front_port=5)
vdp.probe(y,   front_port=6)

vdp.measure(mdy)
vdp.measure(y)

print(vdp)

#coeff_correction_factors = [1.04708792, 1.02602164, 1.04792514, 1.03813069, 1.04608511, 1.04093402, 1.0355061 , 1.04633566, 1.05569066, 1.05238481, 1.04134752, 1.04767382, 1.04842814, 1.04993994, 1.0452508 , 1.06047412, 1.07139706, 1.04458435, 1.04043818, 1.05263836, 1.0525538 , 1.04283895, 1.04725535, 1.05407749, 1.09566963, 1.0882099 , 1.09860859, 1.31937427, 1.0917451 , 1.09011065, 1.09429735, 1.09065486]

for route in vdp.routes:
    #old_coeff = route.coeff
    #route.coeff *= coeff_correction_factors[route.lane]
    #print(f"{old_coeff=} -> {route}")
    #if abs(route.coeff) <= 1:
    #    route.coeff *= 0.1
    print(f"lucidac.route({route.uin}, {route.lane}, {route.coeff}, {route.iout});")
    pass

hc = LUCIDAC()
hc.sock.sock.debug_print = True
hc.reset_circuit(dict(keep_calibration=False))

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

config = vdp.generate()

config["/0"]["/M1"]["calibration"] = {
    "offset_x": [0, 0, 0, 0],
    "offset_y": [0, 0, 0, 0],
    "offset_z": [-0.035, -0.027, -0.029, -0.030]
}

import json

print(json.dumps(config))

# ALL values upscaled
#config["/0"]["/I"]["upscaling"] = [True]*32

hc.one_shot_daq() # this initializes the daq

hc.set_circuit( config,
#    calibrate_mblock = True,
#    calibrate_routes= True # do not use this
)




static_analysis = False

if static_analysis:
    hc.manual_mode("ic")
    from time import sleep
    sleep(0.3)
    print(hc.one_shot_daq())
    
    
else:
    manual_control = True

    if manual_control:
        hc.manual_mode("ic")
        from time import sleep
        sleep(0.3)
        hc.manual_mode("op")
    else:
        #hc.run_config.repetitive = True
        hc.run_config.streaming = False
        hc.run_config.no_streaming = True
        #hc.run_config.write_run_state_changes = False
        
        hc.run_config.ic_time_us = 200
        hc.run_config.op_time_ms = 6
        
        hc.run_config.ic_time = 0 # do not add
        hc.run_config.op_time = 0 # do not add
        
        from pylab import *
        
        #ion()

        run = hc.start_run()
        data = array(run.data())
    
        dso_colors = ["#fffe05", "#02faff", "#f807fb", "#007bff" ] # Rigol DHO14 ;)
        plt.style.use("dark_background")
        plt.title("LUCIDAC Real Hardware: Van-der-Pol oscillator")
        plt.plot(data[:,0], label="mdy", color=dso_colors[0])
        plt.plot(data[:,1], label="y_out", color=dso_colors[1])
        plt.axhline(0, color="white")
        plt.xlabel("Arbitrary units")
        plt.legend()
        plt.show()
