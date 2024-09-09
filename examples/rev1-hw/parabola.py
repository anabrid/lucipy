#!/usr/bin/env python3

from lucipy import *
from time import sleep

test = Circuit()

t = test.int(ic = +1)
t2 = test.int(ic = -1)
m = test.mul(id=3)
c = test.const(1)

l0, l1 = 0, 1

test.route(c, l0, -1, t)
test.route(t, l1, -2, t2)

test.route(t, 2, 1.0, m.a)
test.route(t, 3, 1.0, m.b)

#test.measure(x)
#test.measure(y)

test.probe(t, front_port=5)
test.probe(t2, front_port=6)
test.probe(m, front_port=7)


hc = LUCIDAC()

hc.reset_circuit(dict(keep_calibration=False))

#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

config = test.generate()

#config["/0"]["/M1"]["calibration"] = {
#    "offset_x": [0.1, 0.05, 0.05, 0.04],
#    "offset_y": [0.05, 0, 0, 0],
#    "offset_z": [-0.035, -0.027, -0.029, -0.030]
#}

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
    hc.set_op_time(us=200)

    # for k0 slow:
    #hc.run_config.ic_time_ms = 10
    #hc.run_config.op_time_ms = 20
    #hc.run_config.op_time = 0 # additional ns
    #hc.run_config.ic_time = 0 # additional ns

    # always:
    hc.run_config.repetitive = True
    hc.run_config.streaming = False
    hc.run_config.write_run_state_changes = False
    
    #hc.stop_run()
    run = hc.start_run()


