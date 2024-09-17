#
# Hindmarsh-Rose model of neural bursting and spiking (see
# https://analogparadigm.com/downloads/alpaca_28.pdf for details).
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

hr = Circuit()                          # Create a circuit

mx  = hr.int(ic = 1)
y   = hr.int(ic = 1)
mz  = hr.int(slow = True, ic = -1)
x2  = hr.mul(1)
mx3 = hr.mul(2)
c   = hr.const()

hr.connect(c,   mx)
hr.connect(mx3, mx, weight = 4)
hr.connect(x2,  mx, weight = 6)
hr.connect(y,   mx, weight = 7.5)
hr.connect(mz,  mx)

hr.connect(mx, mx3.a)
hr.connect(x2, mx3.b)

hr.connect(mx, x2.a)
hr.connect(mx, x2.b)

hr.connect(x2, y, weight = 1.333)
hr.connect(c,  y, weight = -0.066)
hr.connect(y,  y)

hr.connect(mx, mz, weight = -0.4)
hr.connect(c,  mz, weight = 0.32)
hr.connect(mz, mz, weight = 0.1)

hr.probe(mx, front_port=0, weight=-1)
hr.probe(y,  front_port=1)
hr.probe(mz, front_port=2, weight=-1)

hc = LUCIDAC()

hc.set_circuit(hr)

hc.manual_mode("ic")
from time import sleep
sleep(0.2)
hc.manual_mode("op")

