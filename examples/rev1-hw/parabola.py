#!/usr/bin/env python3

from lucipy import *
from time import sleep

test = Circuit()

slow = True # test slow time constant

t  = test.int(ic = +1, slow=slow, id=6)
t2 = test.int(ic = -1, slow=slow, id=7)
m  = test.mul(id=3)
c  = test.const(1)

l0, l1 = 0, 1

test.route(c, l0, -1, t)
test.route(t, l1, -2, t2)

test.route(t, 2, 1.0, m.a)
test.route(t, 3, 1.0, m.b)

#test.measure(x)
#test.measure(y)

test.probe(t,  front_port=0)
test.probe(t2, front_port=1)
test.probe(m,  front_port=2)


hc = LUCIDAC()
hc.sock.sock.debug_print = True

hc.reset_circuit(dict(keep_calibration=False))

#hc.set_by_path(["0", "SH"], {"state": "TRACK"})
#hc.set_by_path(["0", "SH"], {"state": "INJECT"})

config = test.generate()

if True:
    config["/0"]["/M1"]["calibration"] = {
        "offset_x": [ 0.0   ,  -0.0049 ,  -0.007  ,  -0.005], # !!! offset_x = input B !!!
        "offset_y": [ 0.1   ,   0.005  ,   0.004  ,   0.0  ], # !!! offset_y = input A !!!
        "offset_z": [ -0.035,  -0.031  ,  -0.028  ,  -0.03 ],      
        "write_eeprom": True,
    }
    hc.circuit_options.mul_calib_kludge = False
    

print(config)

hc.circuit_options.reset_circuit = True
hc.circuit_options.sh_kludge = True

hc.set_circuit(
    config,
#    calibrate_offset = True,
    #   calibrate_routes = True,  #<--- in ulm
#    calibrate_mblock = True,
)

print("CIRCUIT GET:", hc.get_circuit())

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_run(halt_on_overload=False, ic_time=200_000)
    hc.set_op_time(us=200)

    # for k0 slow:
    if slow:
        hc.run_config.ic_time_ms = 10
        hc.run_config.op_time_ms = 20
        hc.run_config.op_time = 0 # additional ns
        hc.run_config.ic_time = 0 # additional ns

    # always:
    hc.run_config.repetitive = True
    hc.run_config.streaming = False
    hc.run_config.write_run_state_changes = False
    hc.run_config.calibrate = False  #<!-- das haben sie in ulm an
    
    #hc.stop_run()
    run = hc.start_run()


