#
# Hyperjerk system 4.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

hj = Circuit()                          # Create a circuit

mddddx = hj.int()
dddx   = hj.int()
mddx   = hj.int()
dx     = hj.int()
mx     = hj.int()
x2     = hj.mul()
c      = hj.const()

hj.connect(c,      mddddx, weight = -0.25)
hj.connect(x2,     mddddx)
hj.connect(dx,     mddddx, weight = -2.44)
hj.connect(mddx,   mddddx)
hj.connect(dddx,   mddddx, weight = -4.71)
hj.connect(mddddx, mddddx)

hj.connect(mddddx, dddx, weight = 1.5)

hj.connect(dddx, mddx, weight = 2.5)

hj.connect(mddx, dx)

hj.connect(dx, mx, weight = 2)

hj.connect(mx, x2.a)
hj.connect(mx, x2.b)

sim     = Simulation(hj)                # Create simulation object
t_final = 400

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mddddx_out, dddx_out, mddx_out, dx_out, mx_out = result.y[mddddx.id], result.y[dddx.id], result.y[mddx.id], result.y[dx.id], result.y[mx.id]
plt.plot(mddddx_out, dx_out)            # Create a phase space plot.

plt.show()                              # Display the plot.

