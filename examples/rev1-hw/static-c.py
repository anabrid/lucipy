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

upscaling = 1 # cannot work because value 10 -> ID -> overload :-)
test_steps = upscaling * linspace(-10, 10, num=20) # dt=0.1
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
ion()

# make it more convenient
measured = rmat.T
expected = test_steps[::-1] / 10 # if upscaling was used

abs_error = measured - expected
rel_error = measured / expected

# show the errors
subplot(2,1,1)
title("Absolute error")
imshow(abs_error.T, vmin=-0.1, vmax=+0.1)
yticks(arange(len(test_steps)), ["%.2f"%x for x in expected])
colorbar()

subplot(2,1,2)
title("Relative error")
imshow(rel_error.T, vmin=0.85, vmax=+1.05)
yticks(arange(len(test_steps)), ["%.2f"%x for x in expected])
colorbar()

# manually calibrate the cblock:
missing_gain = (abs(abs_error[:,-1]) + abs(abs_error[:,0]))/2
correction_factor = 1/(1 - missing_gain)



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
