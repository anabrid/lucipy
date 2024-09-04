#!/usr/bin/env python3

from lucipy import *
from time import sleep

test = Circuit()

t = test.int(ic = +1)
t2 = test.int(ic = -1)
t2m = test.mul(id=3)
c = test.const(1)

l0, l1, l2, l3 = 0, 8, 9, 10

test.route(c, l0, -1, t)
test.route(t, l1, -2, t2)

test.route(t, l2, 1, t2m.a)
test.route(t, l3, 1, t2m.b)

test.probe(t,   front_port=5)
test.probe(t2,  front_port=6)
test.probe(t2m, front_port=7)

#test.measure(t)
#test.measure(t2)
#test.measure(t2m)

hc = LUCIDAC() # ("emu:/")
print(f"Computing at {hc}")
hc.slurp()

hc.reset_circuit()

config = test.generate()

print(config)

hc.set_circuit(
    config,
#    calibrate_offset = True,
#    calibrate_routes = True,
#    calibrate_mblock = True,
)

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)

if 0:
    hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
    hc.set_op_time(us=1000)

    run = hc.start_run()

    from pylab import *
    t, t2, t2m = array(run.data()).T

    figure()
    plot(t, label="t")
    plot(t2, label="t2")
    plot(t2m, label="t2m")
    legend()
    ylim(0,1)
    show()

# for k0 fast
hc.run_config.ic_time_us = 200
hc.run_config.op_time_us = 200

# for k0 slow:
#hc.run_config.ic_time_ms = 10
#hc.run_config.op_time_ms = 20

# always:
hc.run_config.repetitive = True
hc.run_config.no_streaming = True
hc.run_config.write_run_state_changes = False

hc.run_config.op_time = 0 # additional ns
hc.run_config.ic_time = 0 # additional ns


hc.start_run()
print("Rep Mode started")

# just regularly flush to avoid buffer overrun...
try:
    while True:
        hc.slurp()
except KeyboardInterrupt:
    hc.slurp()
    hc.query("stop_run")
