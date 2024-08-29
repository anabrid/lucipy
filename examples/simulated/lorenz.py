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

l = Circuit()                           # Create a circuit

mx    = l.int(ic = 1)
my    = l.int()
mz    = l.int()
xy    = l.mul()
mxs   = l.mul()
const = l.const()

l.connect(mx, mx)
l.connect(my, mx, weight = -1.8)

l.connect(mx, xy.a)
l.connect(my, xy.b)

l.connect(xy, mz, weight = 1.5)
l.connect(mz, mz, weight = 0.2667)

l.connect(mx,    mxs.a)
l.connect(mz,    mxs.b, weight = -2.68)
l.connect(const, mxs.b, weight = -1)

l.connect(mxs, my, weight = 1.536)
l.connect(my,  my, weight = 0.1)

sim     = Simulation(l)                 # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]
plt.plot(mx_out, mz_out)                  # Create a phase space plot.

plt.show()                              # Display the plot.

