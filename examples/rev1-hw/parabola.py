#!/usr/bin/env python3

from lucipy import *
from time import sleep

test = Circuit()

x = test.int(ic = +1)
y = test.int(ic = -1)
c = test.const(1)

l0, l1 = 0, 1

test.route(c, l0, -.1, x)
test.route(x, l1, -.4, y)

test.probe(x, front_port=5)
test.probe(y, front_port=6)

test.measure(x)
test.measure(y)


hc = LUCIDAC()

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
else:
    hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
    hc.set_op_time(us=2000)

    run = hc.start_run()

    from pylab import *
    x, y = array(run.data()).T

    figure()
    plot(x,"-")
    plot(y)
    show()


