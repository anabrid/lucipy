#
# This example implements the Halvorsen attractor defined by 
#
# x' = -ax - 4y -4z - y^2
# y' = -ay - 4z -4x - z^2
# z' = -az - 4x -4z - x^2
# 
# with a = 1.89.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

a  = 1.89

h  = Circuit()

x  = h.int(ic = 0.3)
y  = h.int(ic = 0.1)
z  = h.int(ic = 0.3)
x2 = h.mul()
y2 = h.mul()
z2 = h.mul()

h.connect(x, x2.a, weight = -1)
h.connect(x, x2.b)

h.connect(y, y2.a, weight = -1)
h.connect(y, y2.b)

h.connect(z, z2.a, weight = -1)
h.connect(z, z2.b)

h.connect(x,  x, weight = -a / 10)
h.connect(y,  x, weight = -0.4)
h.connect(z,  x, weight = -0.4)
h.connect(y2, x, weight = -1.5)

h.connect(y,  y, weight = -a / 10)
h.connect(z,  y, weight = -0.4)
h.connect(x,  y, weight = -0.4)
h.connect(z2, y, weight = -1.5)

h.connect(z,  z, weight = -a / 10)
h.connect(x,  z, weight = -0.4)
h.connect(y,  z, weight = -0.4)
h.connect(x2, z, weight = -1.5)


# Run simulation
sim     = Simulation(h)             # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

plt.plot(x_out, y_out)              # Create a phase space plot.
plt.show()                          # Display the plot.

