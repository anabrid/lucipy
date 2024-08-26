#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep 
from pylab import *

# M0 = M-Block INT
# M1 = M-Block MUL

sinus = Circuit()

i0 = sinus.int(id=2, ic=+1)
i1 = sinus.int(id=4, ic=0)

# ask for explicit lanes, for testing
sinus.route(i0, 2,  0.25, i1)
sinus.route(i1, 3, -0.5,  i0)

# this is where we currently have our DSO connected
sinus.probe(i0, front_port=6)
sinus.probe(i1, front_port=7)

# register ADC channels
sinus.measure(i0)
sinus.measure(i1)

print(sinus)

hc = LUCIDAC()
hc.reset_circuit()

config = sinus.generate(skip="/M1")
hc.set_circuit_alt(config)

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    sleep(0.5)
else:
    sample_rate = 125_000
    hc.set_daq(num_channels=2, sample_rate=sample_rate)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_800_000) # op time 0.9ms!
    
    # activate Non-FlexIO code
    hc.run_config.no_streaming = True

    run = hc.start_run()
    data = array(run.data())
    
    #ion()
    clf()
    title(f"{len(data)} Punkte mit {sample_rate=}")
    plot(data[:,0], "o-", label="Channel 0")
    plot(data[:,1], "o-", label="Channel 1")
    legend()
    show()
    

