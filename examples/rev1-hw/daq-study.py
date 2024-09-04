#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep 
from pylab import *
from itertools import product

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

def run_with(op_time_us, sample_rate_per_sec):
    hc.set_daq(num_channels=2, sample_rate=sample_rate_per_sec)
    hc.set_run(halt_on_overload=False, ic_time=200_000)
    hc.set_op_time(us=op_time_us)
    
    # activate Non-FlexIO code
    #hc.run_config.streaming = False
    
    optime_ns = hc.run_config.op_time 
    optime_us = optime_ns / 1000
    optime_sec = optime_us / 1e6
    expected_points = int(optime_sec * sample_rate_per_sec)

    run = hc.start_run()
    try:
        data = array(run.data())
    except:
        return expected_points, 0, False
    

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
    
    return expected_points, len(data), correct

    ion()    
    figure()
    clf()
    title(f"REV1-DAQ-Test mit {sample_rate=} und {optime_us=}")
    suptitle(f"{correct=}; {points}")
    plot(x_hw, "o", label="Channel 0")
    plot(y_hw, "o", label="Channel 1")
    plot(x_sim, "-", label="Simulated 0")
    plot(y_sim, "-", label="Simulated 1")
    legend()
    show()

test_optimes_us = [
    1, 10, 100, 999
]

test_sample_rates = [
    10, 50, 100, 1000, 10_000, 12_500, 20_000, 40_000, 100_000, 1_000_000
]

# or:

#test_sample_rates = LUCIDAC.allowed_sample_rates

combinations = product(test_optimes_us, test_sample_rates)

print("op_time_us sample_rate_per_sec expected_points real_points correct")
for op_time_us, sample_rate_per_sec in combinations:
    expected_points = int(op_time_us/1e6 * sample_rate_per_sec)
    if expected_points < 1:
        continue
    
    # useful print if Teensy just crashes:
    #print("# Now testing...", op_time_us, sample_rate_per_sec, expected_points)
    expected_points, real_points, correct = run_with(op_time_us, sample_rate_per_sec)

    print(op_time_us, sample_rate_per_sec, expected_points, real_points, correct)
