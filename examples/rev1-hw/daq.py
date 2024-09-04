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
adc0 = sinus.measure(i0)
adc1 = sinus.measure(i1)

#print(sinus)

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
    hc.set_run(halt_on_overload=False, ic_time=200_000)
    hc.set_op_time(us=900)
    
    # activate Non-FlexIO code
    hc.run_config.streaming = False

    run = hc.start_run()
    data = array(run.data())
    
    expected_points = int(hc.run_config.op_time/1e9 * sample_rate)
    optime_us = hc.run_config.op_time / 1e3
    optime_sec = hc.run_config.op_time / 1e9
    exactly_all = expected_points == len(data)
    if exactly_all:
        points = f"Alle {len(data)} Punkte"
    else:
        points = f"Nur {len(data)} von erwarteten {expected_points} Punkten"
    
    t_hw = linspace(0, optime_sec, len(data))
    x_hw, y_hw = data[:,adc0], data[:,adc1]
    
    integrators_sim = Simulation(sinus, realtime=True).solve_ivp(optime_sec, dense_output=True).sol(t_hw)
    x_sim, y_sim = integrators_sim[i0.id], integrators_sim[i1.id]
    
    # actual tests
    correct = \
        np.allclose(x_sim, x_hw, atol=0.2, rtol=0.1) and \
        np.allclose(y_sim, y_hw, atol=0.2, rtol=0.1)
    
    #ion()
    clf()
    title(f"REV1-DAQ-Test mit {sample_rate=} und {optime_us=}")
    suptitle(f"{correct=}; {points}")
    plot(x_hw, "o", label="Channel 0")
    plot(y_hw, "o", label="Channel 1")
    plot(x_sim, "-", label="Simulated 0")
    plot(y_sim, "-", label="Simulated 1")
    legend()
    show()
    

