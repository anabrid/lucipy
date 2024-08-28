from lucipy import LUCIDAC

from pylab import *
from itertools import product

import sys
sys.path.append("../test")
from test_hardware import measure_ramp

hc = LUCIDAC()

slopes = [+1, -1]
lanes = range(32)

ion()

res = []

for slope, lane in product(slopes, lanes):
    hc.reset_circuit()
    valid_endpoint, valid_evolution, x = measure_ramp(hc, slope, lane, const_value=-1)
    
    label = f"{slope=} {lane=}" if not valid_endpoint or not valid_evolution else None
    plot(x, "o-", label=label)

    ires = (slope, lane, valid_endpoint, valid_evolution)
    res.append([*ires, x])
    print(*ires)

title("Ramp Integration test: Faulty lanes")
legend().set_draggable(True)
