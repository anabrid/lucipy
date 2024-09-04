#
# Van der Pol oscillator
#

from lucipy import Circuit, Simulation, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

eta = 4

vdp = Circuit()

ys = vdp.ints(8)
m  = vdp.mul()

for i in range(8):
    vdp.route(m, i, 0.0, ys[i])
    vdp.measure(ys[i])

vdp.probe(ys[0], front_port=5)
vdp.probe(ys[1], front_port=6)
vdp.probe(ys[2], front_port=7)

hc = LUCIDAC()
hc.reset_circuit()

config = vdp.generate()

hc.set_circuit( config )

manual_control = False

if manual_control:
    hc.manual_mode("ic")
    from time import sleep
    sleep(0.3)
    hc.manual_mode("op")
else:
    #hc.run_config.repetitive = True
    hc.run_config.streaming = False
    #hc.run_config.write_run_state_changes = False
    
    hc.run_config.ic_time_us = 200
    hc.run_config.op_time_ms = 6
    
    hc.run_config.ic_time = 0 # do not add
    hc.run_config.op_time = 0 # do not add
    
    from pylab import *
    
    ion()

    run = hc.start_run()
    data = array(run.data())
   
    dso_colors = ["#fffe05", "#02faff", "#f807fb", "#007bff" ] # Rigol DHO14 ;)
    plt.style.use("dark_background")
    plt.title("LUCIDAC Real Hardware: Van-der-Pol oscillator")
    for i in range(7):
        plt.plot(data[:,i])#, color=dso_colors[0])
    plt.axhline(0, color="white")
    plt.xlabel("Arbitrary units")
