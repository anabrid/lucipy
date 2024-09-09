#
# This example of a three-time-scale system is due to Christian Kuehn, 
# "Multiple Time Scale Dynamics", Springer, 2015, p. 418., see 
# https://analogparadigm.com/downloads/alpaca_44.pdf for details.
#

from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

c1      = 0.5
c2      = 0.4
c3      = 0.5
epsilon = 0.1
mu      = 0.04

ttss = Circuit()


mx    = ttss.int(ic = 1)
my    = ttss.int()
mz    = ttss.int(slow = True)               # Set k_0 = 100 (default is 10^4)
xx    = ttss.mul()
mxxx  = ttss.mul()
const = ttss.const(1)

ttss.connect(my, mx)
ttss.connect(xx, mx, weight = 10 * c2)
ttss.connect(mxxx, mx, weight = 10 * c3)

ttss.connect(mx, my, weight = -epsilon)     # y' = epsilon(x - z)
ttss.connect(mz, my, weight = epsilon)

# z' = epsilon^2(mu - c1 y), the factor 100 results from k_0 = 100 instead of 
# 10^4. Effectively the 100 cancels out with epsilon * epsilon, but this 
# notation makes it possible to vary mu and epsilon without having to rescale 
# the z integrator.

ttss.route(const, 7, epsilon * epsilon * mu * 100, mz)

ttss.connect(my, mz, weight = epsilon * epsilon * c1 * 100)

ttss.connect(mx, xx.a)                      # xx = x^2
ttss.connect(mx, xx.b)

ttss.connect(xx, mxxx.a)                    # mxxx = -x^3
ttss.connect(mx, mxxx.b)

ttss.probe(mx, front_port=5)
ttss.probe(my, front_port=6)
ttss.probe(mz, front_port=7)

print(ttss)

#coeff_correction_factors = [1.04708792, 1.02602164, 1.04792514, 1.03813069, 1.04608511, 1.04093402, 1.0355061 , 1.04633566, 1.05569066, 1.05238481, 1.04134752, 1.04767382, 1.04842814, 1.04993994, 1.0452508 , 1.06047412, 1.07139706, 1.04458435, 1.04043818, 1.05263836, 1.0525538 , 1.04283895, 1.04725535, 1.05407749, 1.09566963, 1.0882099 , 1.09860859, 1.31937427, 1.0917451 , 1.09011065, 1.09429735, 1.09065486]

#for route in ttss.routes:
    #route.coeff *= coeff_correction_factors[route.lane]

print(ttss)

hc = LUCIDAC()

hc.reset_circuit()
#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

conf = ttss.generate()

conf["/0"]["/M1"]["calibration"] = {
    "offset_x": [0.0, 0, 0, 0],
    "offset_y": [0.0, 0, 0, 0],
    "offset_z": [-0.035, -0.027, -0.029, -0.030]
}

hc.set_circuit(conf)

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")
