from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

alpha = 1.7

sprott = Circuit()

mx      = sprott.int(ic = .1)
my      = sprott.int()
mz      = sprott.int()
mxy    = sprott.mul()
yz    = sprott.mul()
const  = sprott.const()

sprott.connect(yz, mx, weight = 10)         # x' = yz

sprott.connect(mx, my, weight = -1)         # y' = x - y
sprott.connect(my, my)

sprott.connect(const, mz, weight = 0.1)     # z' = 1 - xy (scaled!)
sprott.connect(mxy, mz, weight = 10)

sprott.connect(mx, mxy.a)                   # -xy
sprott.connect(my, mxy.b, weight = -1)

sprott.connect(my, yz.a)                    # yz
sprott.connect(mz, yz.b)


print(sprott.to_ascii_art())


import sys
sys.exit(0)

sim     = Simulation(sprott)                # Create simulation object
t_final = 200

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                        t_eval = np.linspace(0, t_final, num = 1000000))

# Get data from x- and y-integrator
x_out, y_out, z_out = result.y[mx.id], result.y[my.id], result.y[mz.id]

plt.plot(z_out, x_out)                     # Create a phase space plot.
#plt.plot(x_out)
#plt.plot(y_out)
#plt.plot(z_out)
#plt.show()                                  # Display the plot.


