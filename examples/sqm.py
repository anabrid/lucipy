from lucipy import Circuit, Simulation, LUCIDAC, Route
import matplotlib.pyplot as plt
import numpy as np

alpha = 1.7

sqm = Circuit()

# ACHTUNG, schauen ob int(), mul(), etc ueberhaupt auf REV1 gehen!

x     = sqm.int()
y     = sqm.int()
z     = sqm.int()
xsq   = sqm.mul()
const = sqm.const()

sqm.connect(z, x, weight = -1)              # x' = -z
sqm.connect(xsq, y, weight = 2.66)          # y' = -2.666x^2 - y
sqm.connect(y, y, weight = -1)
#sqm.connect(const, z, weight = alpha / 4)   # z' = alpha/4 + alpha*x + 0.15y
sqm.connect(x, z, weight = alpha)
sqm.connect(y, z, weight = 1.5)
sqm.connect(x, xsq.a)                       # Compute -x^2 (multipliers invert)
sqm.connect(x, xsq.b)

sim     = Simulation(sqm)                   # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

#plt.plot(x_out, -y_out)                     # Create a phase space plot.
#plt.show()                                  # Display the plot.


acl_lane = 24 # first ACL lane
wherever = 15 # clane; M1 end, into the void!
for i in range(8):
    sqm.add( Route(x.out, acl_lane+i, 1.0, wherever) )
#sqm.add( Route(y.out, acl_lane+5, 1.0, wherever) )
#sqm.add( Route(z.out, acl_lane+6, 1.0, wherever) )

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k:v for k,v in sqm.generate().items() if not "/M1" in k }

hc = LUCIDAC("tcp://192.168.100.131")
hc.query("reset_circuit")
hc.set_config(config)

# set all ACL channels to external
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
    "acl_select": [ "external" ]*8,
#    "adc_channels": [ i0, i1 ],    
}})


manual_control = True
from time import sleep

if manual_control:
    hc.manual_mode("ic")
    sleep(1)
    hc.manual_mode("op")
    sleep(20)
    hc.manual_mode("halt")
else:
    hc.set_daq(num_channels=2)
    nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

    run = hc.start_run()

