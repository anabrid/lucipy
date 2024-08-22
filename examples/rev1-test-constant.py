#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep 

# M0 = M-Block INT
# M1 = M-Block MUL

### attention, do not use rev1.int() and friends as this is still
###     in REV0 numeration (where M1 and M0 are swapped)

i0, i1 = 2,4

hc = LUCIDAC()
print(hc)

rev1 = Circuit()
rev1.use_constant()

rev1.add( Route(14, 29, -1.0, 0) )
rev1.add( Route(14, 30, -1.0, 0) )
rev1.add( Route(14, 31, -1.0, 0) )

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
