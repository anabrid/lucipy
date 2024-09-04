#!/usr/bin/env python

from lucipy import *

circuit = Circuit()

m0, m1, m2, m3 = circuit.muls(4)
const = circuit.const()

# 0*0: Empty inputs
circuit.connect(const, m0.a, weight=0.1)
circuit.connect(const, m0.b, weight=0.1)

# 0*1
circuit.connect(const, m1.a, weight=1)
circuit.connect(const, m1.b, weight=0.1)

# 0*(-1)
circuit.connect(const, m2.a, weight=-1)
circuit.connect(const, m2.b, weight=0.1)

circuit.measure(m0)
circuit.measure(m1)
circuit.measure(m2)

hc = LUCIDAC()
hc.set_config(circuit.generate())

measurements = hc.one_shot_daq()
print(measurements)
