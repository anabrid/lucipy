#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from lucipy.circuits import Mul
from time import sleep 

# M0 = M-Block INT
# M1 = M-Block MUL

### attention, do not use rev1.int() and friends as this is still
###     in REV0 numeration (where M1 and M0 are swapped)

# Mul are on M1 slot
m0 = Mul(0, 8, 8,   9) # output 8 gets input 8 and 9
m1 = Mul(1, 9, 10, 11) 
m2 = Mul(2,10, 12, 13)
m3 = Mul(3,11, 14, 15)

hc = LUCIDAC()
print(hc)

def mul(a,b):
    rev1 = Circuit()

    rev1.use_constant()

    # we take all our constants from horizontal cross lane 14,
    # that means they are available on vertical lanes 16..32
    const_clane = 14

    # "good" lanes for ACL_OUT
    dso0, dso1, dso2 = 29, 30, 31

    # lanes
    const_a = 16
    const_b = 17
    
    # multiplier
    m = m1

    # Factors
    #a, b = +1.0, +1.0

    rev1.add( Route(const_clane, const_a, a, m.a) )
    rev1.add( Route(const_clane, const_b, b, m.b) )

    sink = 0 # first integrator
    rev1.add( Route(const_clane, dso0, a, sink) )
    rev1.add( Route(const_clane, dso1, b, sink) )
    rev1.add( Route(m.out, dso2, 1.0, sink) )

    print(rev1)

    hc.reset_circuit()

    # filter out M1 because there is nothing to set
    # and MCU complains if I try to configure something nonexisting
    config = { k:v for k,v in rev1.generate().items() if not "/M1" in k }

    print(config)

    hc.set_config(config)

"""
# set all ACL channels to external
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
    "acl_select": [ "external" ]*8,
    "adc_channels": [ i0, i1 ],    
}})



manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    sleep(0.5)
else:
    hc.set_daq(num_channels=2, sample_rate=125_000)
    nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

    run = hc.start_run()

sinus(2,4)
"""
