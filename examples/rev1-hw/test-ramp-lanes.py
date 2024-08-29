from lucipy import LUCIDAC

from pylab import *
from itertools import product

import sys
sys.path.append("../test")
from test_hardware import measure_ramp

hc = LUCIDAC()

#slopes = [+1, -1]
slopes = linspace(-1, 1, num=20).tolist()
lanes = range(26,32)

#ion()

res = []
for lane in lanes:
    clf()
    for slope in slopes:
        hc.reset_circuit()
        valid_endpoint, valid_evolution, x = measure_ramp(hc, slope, lane, const_value=-1)
        
        label = f"{slope=}" if not valid_endpoint or not valid_evolution else None
        title(f"{lane=} Ramp test")
        plot(x, "o-", label=label)

        ires = (slope, lane, valid_endpoint, valid_evolution)
        res.append([*ires, x])
        print(*ires)
    legend()
    savefig(f"ramp-test-{lane=}.png")

#legend().set_draggable(True)
