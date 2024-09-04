#
# Hunter Prey population dynamics (Lotka-Volterra system)
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

eta = 4

lv = Circuit()

h  = lv.int(ic = 0.6)
l  = lv.int(ic = 0.6)
hl = lv.mul()

lv.connect(h,  h, weight=-0.365) # alpha
lv.connect(hl, h, weight=-0.95)  # beta
lv.connect(l,  l, weight=+0.09)  # gamma
lv.connect(hl, l, weight=+0.84)  # delta

lv.connect(h, hl.a, weight=-1)
lv.connect(l, hl.b, weight=-1)


# Run simulation
sim     = Simulation(lv)                  # Create simulation object
t_final = 100

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                       # t_eval = np.linspace(0, t_final, num = 1000000))
                       )

# Get data from x- and y-integrator
h_out, l_out = result.y[h.id], result.y[l.id]

plt.plot(result.t, h_out)
plt.plot(result.t, l_out)
plt.show()                                  # Display the plot.

