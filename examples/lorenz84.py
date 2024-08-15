from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

l = Circuit()

x     = l.int(ic = 1)
y     = l.int()
z     = l.int()
xz   = l.mul()
xy   = l.mul()
yy   = l.mul()
zz   = l.mul()
const = l.const()

l.connect(x, xz.a, weight = -1)             # xz
l.connect(z, xz.b)
l.connect(x, xy.a, weight = -1)             # xy
l.connect(y, xy.b)
l.connect(y, yy.a, weight = -1)             # y^2
l.connect(y, yy.b)
l.connect(z, zz.a, weight = -1)             # z^2
l.connect(z, zz.b)

l.connect(yy, x, weight = -4.5)             # x' = -y^2 - z^2 - ax + af
l.connect(zz, x, weight = -4.5)
l.connect(x, x, weight = -.25)
l.connect(const, x, weight = 1)

l.connect(xy, y, weight = 2)                # z' = xy - bxz - y + g # evtl -0.2?
l.connect(xz, y, weight = -8)
l.connect(y, y, weight = -1)
l.connect(const, y, weight = 0.333)

l.connect(xy, z, weight = 8)                # z' = bxy + xz - z
l.connect(xz, z, weight = 2)
l.connect(z, z, weight = -1)

sim     = Simulation(l)                     # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

plt.plot(x_out, y_out)                      # Create a phase space plot.
plt.show()                                  # Display the plot.

