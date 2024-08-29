#
# Roessler attractor on LUCIDAC:
#
# x' = -0.8y - 2.3z
# y' = 1.25x + 0.2y
# z' = 0.005 + 15z(x - 0.3796)
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

r = Circuit()                           # Create a circuit

x     = r.int(ic = .066)
my    = r.int()
mz    = r.int()
prod  = r.mul()
const = r.const(1)

r.connect(my,    x, weight = -0.8)
r.connect(mz,    x, weight = -2.3)

r.connect(x,     my, weight = 1.25)
r.connect(my,    my, weight = -0.2)

r.connect(const, mz, weight = 0.005)
r.connect(prod,  mz, weight = 10)
r.connect(prod,  mz, weight = 5)

r.connect(mz,    prod.a, weight = -1)
r.connect(x,     prod.b)
r.connect(const, prod.b, weight = -0.3796)

sim     = Simulation(r)                 # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, my_out, mz_out = result.y[x.id], result.y[my.id], result.y[mz.id]
plt.plot(x_out, my_out)                  # Create a phase space plot.

plt.show()                              # Display the plot.

