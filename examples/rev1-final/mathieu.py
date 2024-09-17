#
# Mathieu's differential equation
# Not part of guidebook (v0.1) but Bernd's favourite equation
# See https://analogparadigm.com/downloads/alpaca_10.pdf
#

from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

# These are the two parameters of Mathieu's equation which have to 
# be varied to get a stability map. 0 <= a <= 8 and 0 <= q <= 5.
a = 4
q = 1.8

# First we need an amplitude stabilised cosine signal. Since we do not have
# limiters at the moment, we use a van der Pol-oscillator for that purpose.
eta = .1                # A small value ensures good spectral cleanliness

m = Circuit()

mdy = m.int()
y   = m.int(ic = -1)
y2  = m.mul()
fb  = m.mul()
c   = m.const()

m.connect(fb, mdy, weight = -eta * 2)   # We need cos(2t), so all inputs 
m.connect(y,  mdy, weight = -0.5 * 2)   # to the integrators get a factor 2.

m.connect(mdy, y, weight = 2 * 2)

m.connect(y, y2.a)
m.connect(y, y2.b)

m.connect(y2,  fb.a, weight = -1)
m.connect(c,   fb.a, weight = 0.25)
m.connect(mdy, fb.b)

# Now for the actual Mathieu equation:
mdym = m.int()
ym   = m.int(ic = 0.1)
p    = m.mul()

m.connect(ym, mdym, weight = -a)
m.connect(p,  mdym, weight = q)

m.connect(mdym, ym)

m.connect(y, p.a)
m.connect(ym, p.b, weight = 2)


m.probe(ym, front_port=0)


hc = LUCIDAC()

hc.set_circuit(m)


hc.manual_mode("ic")
from time import sleep
sleep(0.3)
hc.manual_mode("op")
