#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

ramp = Circuit()

### Idee:
###
### Rampe in REV1 System hochintegrieren.

# M0 = M-Block INT
# M1 = M-Block MUL

### attention, do not use rev1.int() and friends as this is still
###     in REV0 numeration (where M1 and M0 are swapped)

ramp.add( Route(15, 0, -1.0, 0) ) # const input to int
ramp.set_ic(0, +1)

acl_lane = 24 # first ACL lane
ramp.add( Route(0,  acl_lane, 1.0, 10) )
ramp.add( Route(14, acl_lane+1, 1.0, 10) )
ramp.add( Route(15, acl_lane+2, 1.0, 10) ) 

print(ramp)

# the following works ONLY on a REV1

hc = LUCIDAC()
print(hc)
hc.reset_circuit()

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k:v for k,v in ramp.generate().items() if not "/M1" in k }

hc.set_config(config)

# set all ACL channels to external
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
    "acl_select": [ "external" ]*8,
    "adc_channels": [ 0 ],
}})

# register constant
config["/U"]["constant"] = True

manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(1)
    hc.manual_mode("op")
    sleep(1)
    hc.manual_mode("halt")
else:
    hc.set_daq(num_channels=2, sample_rate=125_000)
    nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

    run = hc.start_run()
