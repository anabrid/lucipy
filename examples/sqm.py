from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

alpha = 1.7

sqm = Circuit()

x     = sqm.int()
y     = sqm.int()
z     = sqm.int()
xsq   = sqm.mul()
const = sqm.const()

sqm.connect(z, x, weight = -1)              # x' = -z
sqm.connect(xsq, y, weight = 2.66)          # y' = -2.666x^2 - y
sqm.connect(y, y, weight = -1)
sqm.connect(const, z, weight = alpha / 4)   # z' = alpha/4 + alpha*x + 0.15y
sqm.connect(x, z, weight = alpha)
sqm.connect(y, z, weight = 1.5)
sqm.connect(x, xsq.a)                       # Compute -x^2 (multipliers invert)
sqm.connect(x, xsq.b)

sim     = Simulation(sqm)                   # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

plt.plot(x_out, -y_out)                     # Create a phase space plot.
plt.show()                                  # Display the plot.

