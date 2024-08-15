#
# This example of a three-time-scale system is due to Christian Kuehn, 
# "Multiple Time Scale Dynamics", Springer, 2015, p. 418.
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

c1      = 0.5
c2      = 4
c3      = 5
epsilon = 0.1
mu      = 0.04

ttss = Circuit()

x     = ttss.int(ic = 1)
y     = ttss.int()
z     = ttss.int(slow = True)               # Set k_0 = 100 (default is 10^4)
xx    = ttss.mul()
xxx   = ttss.mul()
const = ttss.const()

ttss.connect(y, x, weight = -1)             # x' = -y + c2 x^2 - c3 x^3
ttss.connect(xx, x, weight = c2)
ttss.connect(xxx, x, weight = -c3)

ttss.connect(x, y, weight = epsilon)        # y' = epsilon(x - z)
ttss.connect(z, y, weight = -epsilon)

# z' = epsilon^2(mu - c1 y), the factor 100 results from k_0 = 100 instead of 
# 10^4. Effectively the 100 cancels out with epsilon * epsilon, but this 
# notation makes it possible to vary mu and epsilon without having to rescale 
# the z integrator.
ttss.connect(const, z, weight = epsilon * epsilon * mu * 100)
ttss.connect(y, z, weight = -epsilon * epsilon * c1 * 100)

ttss.connect(x, xx.a, weight = -1)          # xx = x^2
ttss.connect(x, xx.b)

ttss.connect(xx, xxx.a, weight = -1)        # xxx = x^3
ttss.connect(x, xxx.b)

# Run simulation
sim     = Simulation(ttss)                  # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

#plt.plot(x_out, y_out)                      # Create a phase space plot.
plt.plot(x_out)
plt.plot(y_out)
plt.plot(z_out)
plt.show()                                  # Display the plot.

