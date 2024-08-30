#!/usr/bin/env python3

from lucipy import *
from time import sleep
from itertools import product
import numpy as np

import sys
sys.path.append("../../test")
from test_hardware import measure_ics

hc = LUCIDAC()
#hc.sock.sock.debug_print = True

hc.reset_circuit()
hc.manual_mode("ic")

test_values = [-1, -0.5, 0, +0.5, +1]
test_speed_factors = [False, True]

results = [ measure_ics(hc, ic, slow) for (ic, slow) in product(test_values, test_speed_factors)  ]

print(results)
