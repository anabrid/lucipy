#!/usr/bin/env python

from lucipy import Circuit, LUCIDAC

ramp = Circuit()

int = ramp.int(ic=-0.1)
id  = ramp.identity()

ramp.route(int, 0, +1, id)

# id inverts sign
ramp.probe(id, front_port=5)
ramp.probe(int, front_port=6)

hc = LUCIDAC()
hc.set_circuit(ramp.generate())

hc.manual_mode("ic")

