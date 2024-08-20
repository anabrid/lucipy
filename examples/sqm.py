#
# Sprott SQm system, see Ulmann, "Analog and Hybrid Computer Programming",
# 2nd edition, pp. 160 f.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

alpha = 1.7

sqm = Circuit()                         # Create a circuit

mx = sqm.int()
y  = sqm.int()
mz = sqm.int()
x2 = sqm.mul()
c  = sqm.const()

sqm.connect(mz, mx)

sqm.connect(mx, x2.a)
sqm.connect(mx, x2.b)

sqm.connect(x2, y, weight = 2.666)
sqm.connect(y,  y)

sqm.connect(y,  mz, weight = 1.5)
sqm.connect(mx, mz, weight = -alpha)
sqm.connect(c,  mz, weight = alpha / 4)

sim     = Simulation(sqm)               # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, y_out, mz_out = result.y[mx.id], result.y[y.id], result.y[mz.id]
plt.plot(mx_out, mz_out)                # Create a phase space plot.

plt.show()                              # Display the plot.

