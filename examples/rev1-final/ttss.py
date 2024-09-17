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

ttss.probe(mx, front_port=0)
ttss.probe(my, front_port=1)
ttss.probe(mz, front_port=2)

hc = LUCIDAC()

hc.set_circuit(ttss)

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")
