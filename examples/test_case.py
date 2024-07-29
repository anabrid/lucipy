#!/usr/bin/env python3

import sys
from pprint import pprint
sys.path.append("..") # use that lucipy in parent directory

from lucipy import LUCIDAC, Circuit, Route

hc = LUCIDAC("tcp://192.168.150.127")
ode = Circuit()

hc.query("reset")

ode.int(id=0, ic=1)
ode.int(id=1, ic=1)

# rauslegen auf ACL out, rest egal
ode.add( Route(0, 8, 0.0, 4) )
ode.add( Route(0, 9, 0.0, 4) )

config = ode.generate()
pprint(config)
hc.set_config(config)

hc.run_config.ic_time = 500*1000*1000

hc.set_op_time(ms=900)
hc.start_run()
