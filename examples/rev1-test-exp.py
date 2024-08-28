from lucipy import LUCIDAC

from pylab import *
from itertools import product

import sys
sys.path.append("../test")
from fixture_circuits import measure_exp

hc = LUCIDAC()

# alpha = -1 is a good starting point
alpha = -0.5

ics = [+1,-1]
lanes = range(32)

ion()

res = []

for ic, lane in product(ics, lanes):
    hc.reset_circuit()
    valid_evolution, x_hw, x_sim = measure_exp(hc, alpha=alpha, ic=ic, lane=lane)
    
    label = f"{ic=} {lane=}" if not valid_evolution else None
    plot(x_hw, "o-", label=label)

    ires = (ic, lane, valid_evolution)
    res.append([*ires, x_hw])
    print(*ires)

plot(x_sim, "-", label="sim")
title("Exp decrease: Faulty lanes")
legend().set_draggable(True)

