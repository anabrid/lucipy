#!/usr/bin/env python3

import sys
from pprint import pprint
sys.path.append("..") # use that lucipy in parent directory

from lucipy import Circuit

ode = Circuit()

x = ode.int(ic=2)
y = ode.int()
z = ode.int(ic=-2, slow=True)
mul = ode.mul()

ode.connect(x, y, weight=0.4)
ode.connect(x, x)
ode.connect(z, mul.a)
ode.connect(y, mul.b)
ode.connect(mul, y)

pprint(ode.generate())
