#
# This example implements the Reduced Henon-Heiles attractor (cf. Sprott,
# "Elegant Chaos", pp. 133 f.):
#
# x'' = xy
# y'' = -x^2 + 057y^2
# 
# This is a rare example of a system that should be scaled up in order to
# make the most of the available machine unit interval. In the above unscaled
# version it may serve as a rather good test for machine precision.
#
# To increase precision, dx and dy have been scaled up by 10 in the following
# implementation.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

rhh  = Circuit()

mdx = rhh.int()
mdy = rhh.int()
x   = rhh.int(ic = 0.1)
y   = rhh.int(ic = 0.1)
y2  = rhh.mul()
xy  = rhh.mul()
x2  = rhh.mul()

rhh.connect(x, xy.a)            # xy
rhh.connect(y, xy.b)

rhh.connect(y, y2.a)            # y^2
rhh.connect(y, y2.b)

rhh.connect(x, x2.a)            # x^2
rhh.connect(x, x2.b)

rhh.connect(xy, mdx, weight = 10)

rhh.connect(mdx, x, weight = 0.1)

rhh.connect(x2, mdy, weight = -10)
rhh.connect(y2, mdy, weight = 5.7)

rhh.connect(mdy, y, weight = 0.1)

# Run simulation
sim     = Simulation(rhh)       # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mdx_out, mdy_out, x_out, y_out = result.y[mdx.id], result.y[mdy.id], result.y[x.id], result.y[y.id]

plt.plot(mdx_out, mdy_out)      # Create a phase space plot.
plt.show()                      # Display the plot.

