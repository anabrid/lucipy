#
# Hindmarsh-Rose model of neural bursting and spiking (see
# https://analogparadigm.com/downloads/alpaca_28.pdf for details).
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

hr = Circuit()                          # Create a circuit

mx  = hr.int(ic = 1)
y   = hr.int(ic = 1)
mz  = hr.int(slow = True, ic = -1)
x2  = hr.mul()
mx3 = hr.mul()
c   = hr.const()

hr.connect(c,   mx)
hr.connect(mx3, mx, weight = 4)
hr.connect(x2,  mx, weight = 6)
hr.connect(y,   mx, weight = 7.5)
hr.connect(mz,  mx)

hr.connect(mx, mx3.a)
hr.connect(x2, mx3.b)

hr.connect(mx, x2.a)
hr.connect(mx, x2.b)

hr.connect(x2, y, weight = 1.333)
hr.connect(c,  y, weight = -0.066)
hr.connect(y,  y)

hr.connect(mx, mz, weight = -0.4)
hr.connect(c,  mz, weight = 0.32)
hr.connect(mz, mz, weight = 0.1)

sim     = Simulation(hr)                # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, y_out, mz_out = result.y[mx.id], result.y[y.id], result.y[mz.id]
plt.plot(mx_out)
plt.plot(y_out)
plt.plot(mz_out)

plt.show()                              # Display the plot.

