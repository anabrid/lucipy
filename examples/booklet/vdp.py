#
# Van der Pol oscillator
# neither part of the booklet nor is there an analog paradigm application note
#

from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

eta = 4

vdp = Circuit()

mdy = vdp.int()
y   = vdp.int(ic = 0.1)
y2  = vdp.mul(1)
fb  = vdp.mul(2)
c   = vdp.const()

vdp.connect(fb, mdy, weight = -eta)
vdp.connect(y,  mdy, weight = -0.5)

vdp.connect(mdy, y, weight = 2)

vdp.connect(y, y2.a)
vdp.connect(y, y2.b)

vdp.connect(y2,  fb.a, weight = -1)
vdp.connect(c,   fb.a, weight = 0.25)
vdp.connect(mdy, fb.b)

vdp.probe(mdy, front_port=0)
vdp.probe(y,   front_port=1)

vdp.measure(mdy)
vdp.measure(y)

hc = LUCIDAC()


if 1:
    hc.set_circuit(vdp)

    hc.manual_mode("ic")
    from time import sleep
    sleep(0.3)
    hc.manual_mode("op")
