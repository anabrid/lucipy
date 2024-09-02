from lucipy import LUCIDAC

from pylab import *
from itertools import product


import sys
sys.path.append("../../test")
from fixture_circuits import measure_cblock, measure_cblock_stride_variable


###
### Static test for the Coefficients.
###

hc = LUCIDAC()

hc.reset_circuit()
hc.manual_mode("ic")

lanes = range(32) # this is not changeable at this test!

simple_uin_one_output = True
if simple_uin_one_output:
    upscaling = 1 # cannot work because value 10 -> ID -> overload :-)
    test_steps = upscaling * linspace(-1, 1, num=6) # dt=0.1
    rmat = np.ndarray((len(test_steps), len(lanes)))

    for i,val in enumerate(test_steps):
        print(val)
        test_values = [val]*len(lanes)
        res = measure_cblock(hc, test_values)
        print(res)
        rmat[i,:] = res

    correctness = isclose(test_steps[:,np.newaxis], -rmat, rtol=0.1)
    all_correct = all(correctness)

    imshow(rmat)
    title("Constants on all CBlock lanes: Expected vs measured")
    colorbar()#.set_label("Measured Coeff", rotation=270)
    yticks(arange(len(test_steps)), ["%.2f"%x for x in test_steps])
    ylabel("Expected Coeff")
    xticks(arange(len(lanes)), arange(len(lanes)))
    xlabel("Lane")

    show()

else:
    uin_values = linspace(-1, 1, num=3)
    coeff_values = linspace(-1, 1, num=3)
    rmat = np.ndarray((len(uin_values), len(coeff_values)))
    
    
    lanes = [0,1]
    uin_values = [-0.5, +0.5]
    coeff_values = [-0.5, +0.5]
    res = measure_cblock_stride_variable(hc, lanes, uin_values, coeff_values)
    
    # Looks more or less useful, except the signs!
    print(res)
    
    # TODO: Continue, do a full sampling
    
    # TODO: Does this even make sense?
    #       We can also continue with the ramp tests and just loop them
    #       over multiple coeff values!
    
    #for i,uin in enumerate(uin_values):
    #    for j,coeff in enumerate(coeff_values):
    #        print(i,j,uin,coeff)
    #        measure_cblock_variable
    

"""

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

"""
