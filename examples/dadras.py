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

x  = d.int(ic = 0.06)
y  = d.int(ic = 0.1)
z  = d.int(ic = -0.1)
yz = d.mul()
xz = d.mul()
xy = d.mul()

d.connect(y,  x, weight = 0.1)
d.connect(x,  x, weight = -0.3)
d.connect(yz, x, weight = 5.4)

d.connect(y,  y, weight = 0.17)
d.connect(xz, y, weight = -2)
d.connect(z,  y)

d.connect(xy, z, weight = 4)
d.connect(z,  z, weight = -0.9)

d.connect(y, yz.a)
d.connect(z, yz.b)

d.connect(x, xz.a)
d.connect(z, xz.b)

d.connect(x, xy.a)
d.connect(y, xy.b)

# Run simulation
sim     = Simulation(d)             # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

plt.plot(y_out, z_out)              # Create a phase space plot.
plt.show()                          # Display the plot.

