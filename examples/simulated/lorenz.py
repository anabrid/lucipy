#
# Lorenz attractor on LUCIDAC as defined by the (unscaled) equations
#
# x' = sigma(y - x)
# y' = x(rho - z) - y
# z' = xy - beta z
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

a = 1.0
b = 2.8
c = 2.666 / 10

l = Circuit()                           # Create a circuit

mx = l.int(ic = -0.1)
my = l.int(ic = 0.3)
mz = l.int(ic = 0.5)
xz = l.mul()
xy = l.mul()

l.connect(mx, xz.a)                     # Product -x * -z = xz
l.connect(mz, xz.b, weight = 2)

l.connect(mx, xy.a)                     # Product -x * -y = xy
l.connect(my, xy.b)

l.connect(my, mx, weight = -a)
l.connect(mx, mx, weight = a)

l.connect(mx, my, weight = -b)
l.connect(xz, my, weight = -5)
l.connect(my, my, weight = 0.1)

l.connect(xy, mz, weight = 2.5)
l.connect(mz, mz, weight = c)

sim     = Simulation(l)                 # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]
plt.plot(mx_out, mz_out)                  # Create a phase space plot.
#plt.plot(mx_out)
#plt.plot(my_out)
#plt.plot(mz_out)

plt.show()                              # Display the plot.

