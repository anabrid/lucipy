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

mx  = h.int(ic = -0.3)
my  = h.int(ic = -0.1)
mz  = h.int(ic = -0.3)
x2 = h.mul()
y2 = h.mul()
z2 = h.mul()

h.connect(mx, x2.a)
h.connect(mx, x2.b)

h.connect(my, y2.a)
h.connect(my, y2.b)

h.connect(mz, z2.a)
h.connect(mz, z2.b)

h.connect(mx,  mx, weight = a / 10)
h.connect(my,  mx, weight = 0.4)
h.connect(mz,  mx, weight = 0.4)
h.connect(y2, mx, weight = -1.5)

h.connect(my,  my, weight = a / 10)
h.connect(mz,  my, weight = 0.4)
h.connect(mx,  my, weight = 0.4)
h.connect(z2, my, weight = -1.5)

h.connect(mz,  mz, weight = a / 10)
h.connect(mx,  mz, weight = 0.4)
h.connect(my,  mz, weight = 0.4)
h.connect(x2, mz, weight = -1.5)


# Run simulation
sim     = Simulation(h)             # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]

plt.plot(mx_out, my_out)            # Create a phase space plot.
plt.show()                          # Display the plot.

