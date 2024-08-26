#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

# M0 = M-Block INT
# M1 = M-Block MUL


ramp = Circuit()

integrator = 2
ic = -1
slope = +1

i = ramp.int(id=integrator, ic=ic)
c = ramp.const()

ramp.connect(c, i, weight=slope)

ramp.probe(i, front_port=6)
channel = ramp.measure(i)
print(f"{channel=}")

hc = LUCIDAC()
print(hc)
hc.reset_circuit()

config = ramp.generate(skip="/M1")
hc.set_config(config)

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    sleep(1)
    hc.manual_mode("op")
    sleep(1)
    hc.manual_mode("halt")
else:
    hc.set_daq(num_channels=1, sample_rate=125_000)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=200_000, no_streaming=True)
    
    from pylab import *

    run = hc.start_run()
    data = array(run.data())
    x_run = data.T[channel]
    t_run = linspace(0, 2, len(x_run))
    
    sim = Simulation(ramp)
    sim_data = sim.solve_ivp(2) # in units of k0...
    x_sim = sim_data.y[i.id]
    t_sim = sim_data.t
    
    #ion()
    clf()
    title(f"{len(data)} Punkte")
    plot(t_run, x_run, "o-", label="Hardware")
    plot(t_sim, x_sim, "o-", label="Simulation")
    #plot(t_sim, -x_sim, "o-", label="-Simulation")
    legend()
    show()
