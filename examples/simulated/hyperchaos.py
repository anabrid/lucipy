#
# Hyperchaotic system, including a quartic term.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

hc = Circuit()                          # Create a circuit

mw   = hc.int(ic = .01)
z    = hc.int()
my   = hc.int()
x    = hc.int()
x2   = hc.mul()
x4   = hc.mul()
mwx4 = hc.mul()

hc.connect(mwx4, mw, weight = 1.6)
hc.connect(x,    mw, weight = -0.02)
hc.connect(my,   mw, weight = 0.03)
hc.connect(z,    mw, weight = -0.175)

hc.connect(mw, z, weight = 0.2)

hc.connect(z, my, weight = 0.1666)

hc.connect(my, x, weight = 0.15)

hc.connect(x, x2.a)
hc.connect(x, x2.b)

hc.connect(x2, x4.a)
hc.connect(x2, x4.b)

hc.connect(x4, mwx4.a)
hc.connect(mw, mwx4.b)

sim     = Simulation(hc)                # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mw_out, z_out, my_out, x_out = result.y[mw.id], result.y[z.id], result.y[my.id], result.y[x.id]
#plt.plot(x_out, mw_out)                # Create a phase space plot.

plt.plot(result.t, mw_out, label="mw")
plt.plot(result.t, z_out, label="z")
#plt.plot(my_out)
plt.plot(result.t, x_out, label="x")
plt.legend()

plt.show()                              # Display the plot.

