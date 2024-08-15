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
z     = ttss.int()
xx    = ttss.mul()
xxx   = ttss.mul()
const = ttss.const()

ttss.connect(y, x, weight = -1)             # x' = -y + c2 x^2 - c3 x^3
ttss.connect(xx, x, weight = c2)
ttss.connect(xxx, x, weight = -c3)

ttss.connect(x, y, weight = epsilon)        # y' = epsilon(x - z)
ttss.connect(z, y, weight = -epsilon)

ttss.connect(x, xx.a, weight = -1)          # xx = x^2
ttss.connect(x, xx.b)

ttss.connect(xx, xxx.a, weight = -1)        # xxx = x^3
ttss.connect(x, xxx.b)

# z' = epsilon^2(mu - c1 y)
ttss.connect(const, z, weight = epsilon * epsilon * mu)
ttss.connect(y, z, weight = -epsilon * epsilon * c1)

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

