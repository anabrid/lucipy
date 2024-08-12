#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation

static = Circuit()

# M0 = M-Block ID, instead of INT
# M1 = M-Block MUL, as in normal LUCIDAC

i0 = static.int().out # just an ID lane, input=output

acl_lane = 24 # first ACL lane

# at the ACL line the external signal is fed in
for i in range(8):
    static.add( Route(i0+i, acl_lane+i, 0.1, i0+i) )


print(static)

# the following works ONLY on a REV1

hc = LUCIDAC()
hc.reset_circuit()

# filter out M0 and M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k:v for k,v in static.generate().items() if not "/M" in k }

hc.set_config(config)

# set first ACL channel to external
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": { "acl_select": [ "external"  ] }})


