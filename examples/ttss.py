#
# This example of a three-time-scale system is due to Christian Kuehn, 
# "Multiple Time Scale Dynamics", Springer, 2015, p. 418., see 
# https://analogparadigm.com/downloads/alpaca_44.pdf for details.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

c1      = 0.5
c2      = 0.4
c3      = 0.5
epsilon = 0.1
mu      = 0.04

ttss = Circuit()

mx    = ttss.int(ic = 1)
my    = ttss.int()
mz    = ttss.int(slow = True)               # Set k_0 = 100 (default is 10^4)
xx    = ttss.mul()
mxxx  = ttss.mul()
const = ttss.const()

ttss.connect(my, mx)
ttss.connect(xx, mx, weight = 10 * c2)
ttss.connect(mxxx, mx, weight = 10 * c3)

ttss.connect(mx, my, weight = -epsilon)     # y' = epsilon(x - z)
ttss.connect(mz, my, weight = epsilon)

# z' = epsilon^2(mu - c1 y), the factor 100 results from k_0 = 100 instead of 
# 10^4. Effectively the 100 cancels out with epsilon * epsilon, but this 
# notation makes it possible to vary mu and epsilon without having to rescale 
# the z integrator.
ttss.connect(const, mz, weight = epsilon * epsilon * mu * 100)
ttss.connect(my, mz, weight = epsilon * epsilon * c1 * 100)

ttss.connect(mx, xx.a)                      # xx = x^2
ttss.connect(mx, xx.b)

ttss.connect(xx, mxxx.a)                    # mxxx = -x^3
ttss.connect(mx, mxxx.b)

# Run simulation
sim     = Simulation(ttss)                  # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]

plt.plot(mx_out, mz_out)                    # Create a phase space plot.
#plt.plot(mx_out)
#plt.plot(my_out)
#plt.plot(mz_out)
plt.show()                                  # Display the plot.

