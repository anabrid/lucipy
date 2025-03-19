#
# Hyperchaotic system, including a quartic term.
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

hc = Circuit()                          # Create a circuit

fs = False

mw   = hc.int(slow = fs, ic = .01)
z    = hc.int(slow = fs)
my   = hc.int(slow = fs)
x    = hc.int(slow = fs)
x2   = hc.mul()
x4   = hc.mul()
mwx4 = hc.mul()

hc.connect(mwx4, mw, weight = 0.8)
hc.connect(x,    mw, weight = -0.02)
hc.connect(my,   mw, weight = 0.03)
hc.connect(z,    mw, weight = -0.175)

hc.connect(mw, z, weight = 0.2)

hc.connect(z, my, weight = 0.1666)

hc.connect(my, x, weight = 0.15)
hc.connect(x,  x, weight = 0.007)

hc.connect(x, x2.a, weight = 2)
hc.connect(x, x2.b, weight = 2)

hc.connect(x2, x4.a)
hc.connect(x2, x4.b)

hc.connect(x4, mwx4.a)
hc.connect(mw, mwx4.b, weight = 2)

hc.probe(mw, front_port=0)
hc.probe(x,  front_port=1)
hc.probe(my, front_port=2)
hc.probe(z,  front_port=3)

config = hc.generate()


lucidac = LUCIDAC()
lucidac.set_circuit(hc)

#lucidac.manual_mode("ic")
#from time import sleep
#sleep(0.5)
#lucidac.manual_mode("op")

lucidac.run(op_time_unlimited=True)

