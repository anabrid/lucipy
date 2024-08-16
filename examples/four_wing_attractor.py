#
# This example implements a "four wing attractor" described in Wang, Sun, von 
# Wyk, Qi, van Wyk, "A 3-D four-wing attractor and its analysis", Brazilian 
# Journal of Physics, Vol. 39, No. 3, September 2009.
#
# The general form of this system is
#
# x' = ax + cyz
# y' = bx + dy - xz
# z' = ez + fxy
#
# with parameters a = 0.2, b = -0.01, c = 1, d = -0.4, e = -1, and f = -1.
#
# The scaled system has the form
#
# x' = 0.2x + 3yz
# y' = -0.01x - 0.4y - 3xz
# z' = -z -3xy
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

f  = Circuit()

x  = f.int(ic = .3)
y  = f.int()
z  = f.int()
yz = f.mul()
xz = f.mul()
xy = f.mul()

f.connect(x, x, weight = 0.2)
f.connect(yz, x, weight = 3)

f.connect(x, y, weight = -0.01)
f.connect(y, y, weight = -0.4)
f.connect(xz, y, weight = -3)

f.connect(z, z, weight = -1)
f.connect(xy, z, weight = -3)

f.connect(y, yz.a, weight = -1)         # yz
f.connect(z, yz.b)

f.connect(x, xz.a, weight = -1)         # xz
f.connect(z, xz.b)

f.connect(x, xy.a, weight = -1)         # xy
f.connect(y, xy.b)

# Run simulation
sim     = Simulation(f)                 # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final,
                        method = 'LSODA',
                        t_eval = np.linspace(0, t_final, num = 100000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

#plt.plot(x_out, z_out)                  # Create a phase space plot.
plt.plot(x_out)
plt.plot(y_out)
plt.plot(z_out)
plt.show()                              # Display the plot.
