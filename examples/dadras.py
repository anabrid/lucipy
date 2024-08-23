#
# This example implements the Dadras attractor defined by 
#
# x' = y - px +oyz
# y' = ry - xz + z
# z' = cxy - ez
# 
# with p = 3, o = 2.7, r = 1.7, c = 2, and e = 9.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

d  = Circuit()

mx  = d.int(ic = 0.06)
my  = d.int(ic = 0.1)
mz  = d.int(ic = -0.1)
yz = d.mul()
xz = d.mul()
xy = d.mul()

d.connect(my, yz.a)
d.connect(mz, yz.b)

d.connect(mx, xz.a)
d.connect(mz, xz.b)

d.connect(mx, xy.a)
d.connect(my, xy.b)

d.connect(my, mx, weight = -0.1)
d.connect(mx, mx, weight = 0.3)
d.connect(yz, mx, weight = 5.4)

d.connect(my, my, weight = -0.17)
d.connect(xz, my, weight = -2)
d.connect(mz, my, weight = -0.1)

d.connect(xy, mz, weight = 4)
d.connect(mz, mz, weight = 0.9)

# Run simulation
sim     = Simulation(d)             # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]

plt.plot(my_out, mz_out)            # Create a phase space plot.
plt.show()                          # Display the plot.

