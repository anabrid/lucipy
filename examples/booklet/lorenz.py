# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit
from time import sleep

a = 1.0
b = 2.8
c = 2.666 / 10

l = Circuit()                           # Create a circuit

mx = l.int(ic = -0.1)
my = l.int(ic = 0.3)
mz = l.int(ic = 0.5)
xz = l.mul()
xy = l.mul()

l.connect(mx, xz.a)                     # Product -x * -z = xz
l.connect(mz, xz.b)

l.connect(mx, xy.a)                     # Product -x * -y = xy
l.connect(my, xy.b)

l.connect(my, mx, weight = -a)
l.connect(mx, mx, weight = a*0.8)       # 0.8 increases stability

l.connect(mx, my, weight = -b)
l.connect(xz, my, weight = -5)
l.connect(my, my, weight = 0.1)

l.connect(xy, mz, weight = 5)
l.connect(mz, mz, weight = c)

l.probe(mx, front_port=0)
l.probe(my, front_port=1)
l.probe(mz, front_port=2)

hc = LUCIDAC()
hc.set_circuit(l)

hc.set_op_time(unlimited=True)
hc.start_run()


