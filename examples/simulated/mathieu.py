#
# Mathieu's differential equation
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

# These are the two parameters of Mathieu's equation which have to 
# be varied to get a stability map. 0 <= a <= 8 and 0 <= q <= 5.
a = 3
q = 3

# First we need an amplitude stabilised cosine signal. Since we do not have
# limiters at the moment, we use a van der Pol-oscillator for that purpose.
eta = .1                # A small value ensures good spectral cleanliness

m = Circuit()

mdy = m.int()
y   = m.int(ic = -1)
y2  = m.mul()
fb  = m.mul()
c   = m.const()

m.connect(fb, mdy, weight = -eta * 2)   # We need cos(2t), so all inputs 
m.connect(y,  mdy, weight = -0.5 * 2)   # to the integrators get a factor 2.

m.connect(mdy, y, weight = 2 * 2)

m.connect(y, y2.a)
m.connect(y, y2.b)

m.connect(y2,  fb.a, weight = -1)
m.connect(c,   fb.a, weight = 0.25)
m.connect(mdy, fb.b)

# Now for the actual Mathieu equation:
mdym = m.int()
ym   = m.int(ic = 0.1)
p    = m.mul()

m.connect(ym, mdym, weight = -a)
m.connect(p,  mdym, weight = q)

m.connect(mdym, ym)

m.connect(y, p.a)
m.connect(ym, p.b, weight = 2)

################################################################################
# Run simulation
sim     = Simulation(m)                  # Create simulation object
t_final = 100

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final, 
                        method = 'LSODA', 
                       # t_eval = np.linspace(0, t_final, num = 1000000))
                       )

# Get data from x- and y-integrator
mdy_out, y_out = result.y[mdy.id], result.y[y.id]
ym_out = result.y[ym.id]

dso_colors = ["#fffe05", "#02faff", "#f807fb", "#007bff" ] # Rigol DHO14 ;)
plt.style.use("dark_background")
plt.title("LUCIDAC Simulation: Matthieu's differential equation")
#plt.plot(result.t, y_out, label="y_out", color=dso_colors[0])
plt.plot(result.t, ym_out, label="ym", color=dso_colors[1])
plt.axhline(0, color="white")
plt.xlabel("Simulation time [100us]")
plt.legend()
plt.show()                                  # Display the plot.

