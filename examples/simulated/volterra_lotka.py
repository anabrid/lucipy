#
# Volterra-Lotka system
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

alpha = 0.2
beta  = 0.8
delta = 0.4
zeta  = 0.1

vl = Circuit()

r  = vl.int(ic = .2)
l  = vl.int(ic = .05)
lr = vl.mul()

vl.connect(r, lr.a)
vl.connect(l, lr.b)

vl.connect(r,  r, -alpha)
vl.connect(lr, r, -beta)

vl.connect(l,  l, zeta)
vl.connect(lr, l, delta)

# Run simulation
sim     = Simulation(vl)                # Create simulation object
t_final = 400

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                       # t_eval = np.linspace(0, t_final, num = 1000000))
                       )

# Get data from x- and y-integrator
r_out, l_out = result.y[r.id], result.y[l.id]

dso_colors = ["#fffe05", "#02faff", "#f807fb", "#007bff" ] # Rigol DHO14 ;)
plt.style.use("dark_background")
plt.title("LUCIDAC Simulation: Predator-prey system")
plt.plot(result.t, -r_out, label="Rabbits", color=dso_colors[0])
plt.plot(result.t, -l_out, label="Lynxes", color=dso_colors[1])
plt.axhline(0, color="white")
plt.xlabel("Simulation time [100us]")
plt.legend()
plt.show()                                  # Display the plot.

