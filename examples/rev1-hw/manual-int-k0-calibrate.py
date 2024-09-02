#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep
from lucipy.synchc import RemoteError


hc = LUCIDAC()
hc.reset_circuit()
try:
    hc.slurp()
    hc.query("stop_run")
except RemoteError:
    pass

integrator = 2
lane = 0

#ic, slope = -1, +1
ic, slope = +1, -1

ramp = Circuit()

i = ramp.int(id=integrator, ic=ic)
j= ramp.int(id=integrator+1, ic=ic)
c = ramp.const(1)

ramp.route(c, lane, slope, i.a)
ramp.probe(i, front_port=7)

hc.set_config(ramp.generate())

hc.set_run(ic_time=200_000, op_time=200_000)
hc.run_config.repetitive = True
hc.run_config.no_streaming = True

hc.start_run()
print("Rep Mode started")

# just regularly flush to avoid buffer overrun...
try:
    while True:
        hc.slurp()
except KeyboardInterrupt:
    hc.slurp()
    hc.query("stop_run")
