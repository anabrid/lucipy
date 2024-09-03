#
# Van der Pol oscillator
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

eta = 4

vdp = Circuit()

mdy = vdp.int()
y   = vdp.int(ic = 0.1)
y2  = vdp.mul()
fb  = vdp.mul()
c   = vdp.const()

vdp.connect(fb, mdy, weight = -eta)
vdp.connect(y,  mdy, weight = -0.5)

vdp.connect(mdy, y, weight = 2)

vdp.connect(y, y2.a)
vdp.connect(y, y2.b)

vdp.connect(y2,  fb.a, weight = -1)
vdp.connect(c,   fb.a, weight = 0.25)
vdp.connect(mdy, fb.b)

# Run simulation
sim     = Simulation(vdp)                  # Create simulation object
t_final = 20

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                       # t_eval = np.linspace(0, t_final, num = 1000000))
                       )

# Get data from x- and y-integrator
mdy_out, y_out = result.y[mdy.id], result.y[y.id]

plt.plot(mdy_out)
plt.plot(y_out)
plt.show()                                  # Display the plot.

