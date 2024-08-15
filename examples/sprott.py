from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

alpha = 1.7

sprott = Circuit()

x      = sprott.int(ic = .1)
y      = sprott.int()
z      = sprott.int()
mxy    = sprott.mul()
myz    = sprott.mul()
const  = sprott.const()

sprott.connect(myz, x, weight = -10)        # x' = yz
sprott.connect(x, y)                        # y' = x - y
sprott.connect(y, y, weight = -1)
sprott.connect(const, z, weight = 0.1)      # z' = 1 - xy (scaled!)
sprott.connect(mxy, z, weight = 10)
sprott.connect(x, mxy.a)                    # mxy = -xy
sprott.connect(y, mxy.b)
sprott.connect(y, myz.a)                    # myz = -yz
sprott.connect(z, myz.b)

sim     = Simulation(sprott)                # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[x.id], result.y[y.id], result.y[z.id]

plt.plot(z_out, x_out)                     # Create a phase space plot.
plt.show()                                  # Display the plot.

