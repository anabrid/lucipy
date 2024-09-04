#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep
from lucipy.synchc import RemoteError


hc = LUCIDAC()
hc.reset_circuit()
#hc.sock.sock.debug_print = True

try:
    hc.slurp()
    hc.query("stop_run")
except RemoteError:
    pass

integrator = 7
lane = 0

#ic, slope = -1, +1
ic, slope = +1, -1

ramp = Circuit()

slow = False

i = ramp.int(id=integrator, ic=ic, slow=slow)
#j= ramp.int(id=integrator+1, ic=ic)
c = ramp.const(1)

ramp.route(c, lane, slope, i.a)
ramp.probe(i, front_port=7)

hc.set_config(ramp.generate())

if not slow:
    hc.set_run(ic_time=200_000, op_time=200_000) # for k0 fast
else:
    # for k0 slow:
    hc.run_config.ic_time_ms = 10
    hc.run_config.op_time_ms = 20
    hc.run_config.op_time = 0 # additional ns
    hc.run_config.ic_time = 0 # additional ns

# always:
hc.run_config.repetitive = True
hc.run_config.streaming = False
hc.run_config.write_run_state_changes = False

hc.start_run()
print("Rep Mode started")

# just regularly flush to avoid buffer overrun...
try:
    while True:
        hc.slurp()
except KeyboardInterrupt:
    hc.slurp()
    hc.query("stop_run")
