#
# Van der Pol oscillator
#

from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

eta = 3

vdp = Circuit()

mdy = vdp.int()
y   = vdp.int(ic = 0.1)
y2  = vdp.mul()
fb  = vdp.mul()
c   = vdp.const()

vdp.connect(fb, mdy, weight = -eta)
vdp.connect(y,  mdy, weight = -0.5)

vdp.connect(mdy, y, weight = 2)

vdp.connect(y, y2.a)
vdp.connect(y, y2.b)

vdp.connect(y2,  fb.a, weight = -1)
vdp.connect(c,   fb.a, weight = 0.25)
vdp.connect(mdy, fb.b)

vdp.probe(mdy, front_port=5)
vdp.probe(y,   front_port=6)

#coeff_correction_factors = [1.04708792, 1.02602164, 1.04792514, 1.03813069, 1.04608511, 1.04093402, 1.0355061 , 1.04633566, 1.05569066, 1.05238481, 1.04134752, 1.04767382, 1.04842814, 1.04993994, 1.0452508 , 1.06047412, 1.07139706, 1.04458435, 1.04043818, 1.05263836, 1.0525538 , 1.04283895, 1.04725535, 1.05407749, 1.09566963, 1.0882099 , 1.09860859, 1.31937427, 1.0917451 , 1.09011065, 1.09429735, 1.09065486]

for route in vdp.routes:
    #old_coeff = route.coeff
    #route.coeff *= coeff_correction_factors[route.lane]
    #print(f"{old_coeff=} -> {route}")
    #if abs(route.coeff) <= 1:
    #    route.coeff *= 0.1
    pass

hc = LUCIDAC()

config = vdp.generate()

# ALL values upscaled
#config["/0"]["/I"]["upscaling"] = [True]*32

hc.set_circuit( config )

hc.manual_mode("ic")
from time import sleep
sleep(0.3)
hc.manual_mode("op")

