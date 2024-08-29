from lucipy import LUCIDAC
from lucipy.synchc import LocalError, RemoteError

from pylab import *
from itertools import product

import sys
sys.path.append("../test")
from fixture_circuits import measure_sinus

hc = LUCIDAC()
#hc.sock.sock.debug_print = True

i0, i1 = 2, 4
lanes = range(32)

ion()

res = []
rmat = zeros((32,32))


for l0, l1 in product(lanes, lanes):
    if l0 >= l1: # problem is symmetric
        continue

#l0 = 0
#for l1 in lanes:    
    while True:
        try:
            hc.slurp()
            hc.reset_circuit()
            valid, x_hw, y_hw, x_sim, y_sim = measure_sinus(hc, i0, i1, l0, l1)
            break
        except (LocalError, RemoteError):
            continue
        
    label = f"{l0=} {l1=}" if not valid else None
    plot(x_hw, "o-", label=label)
    plot(y_hw, "o-")

    ires = (l0, l1, valid)
    rmat[l0,l1] = valid
    res.append([*ires, x_hw,y_hw])
    print(*ires)

plot(x_sim, "-", label="Expected")
plot(y_sim, "-")

title("Sinus: Faulty lanes")
legend().set_draggable(True)

figure()
imshow(rmat)

