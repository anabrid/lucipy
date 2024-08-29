#
# This example implements a "four wing attractor" described in Wang, Sun, von 
# Wyk, Qi, van Wyk, "A 3-D four-wing attractor and its analysis", Brazilian 
# Journal of Physics, Vol. 39, No. 3, September 2009.
#
# The general form of this system is
#
# x' = ax + cyz
# y' = bx + dy - xz
# z' = ez + fxy
#
# with parameters a = 0.2, b = -0.01, c = 1, d = -0.4, e = -1, and f = -1.
#
# The scaled system has the form
#
# x' = 0.2x + 3yz
# y' = -0.01x - 0.4y - 3xz
# z' = -z -3xy
#

from lucipy import Circuit, Simulation
import matplotlib.pyplot as plt
import numpy as np

f  = Circuit()

mx  = f.int(ic = .3333)
my  = f.int()
mz  = f.int()
yz  = f.mul()
xz  = f.mul()
xy  = f.mul()

f.connect(mx, mx, weight = -0.2)
f.connect(yz, mx, weight = 3)

f.connect(mx, my, weight = 0.01)
f.connect(my, my, weight = 0.4)
f.connect(xz, my, weight = -3)

f.connect(mz, mz)
f.connect(xy, mz, weight = -3)

f.connect(my, yz.a)
f.connect(mz, yz.b)

f.connect(mx, xz.a)
f.connect(mz, xz.b)

f.connect(mx, xy.a)
f.connect(my, xy.b)

f.measure(mx)
f.measure(my)
f.measure(mz)

# Run simulation
sim     = Simulation(f)                 # Create simulation object
t_final = 1000

#  The integration scheme used has a significant impact on the correctness of 
# the solution as does the interval between time steps.
result  = sim.solve_ivp(t_final,
                        method = 'LSODA',
                        t_eval = np.linspace(0, t_final, num = 100000))

# Get data from x- and y-integrator
mx_out, my_out, mz_out = result.y[mx.id], result.y[my.id], result.y[mz.id]

plt.plot(my_out, mz_out)                  # Create a phase space plot.
#plt.plot(mx_out)
#plt.plot(my_out)
#plt.plot(mz_out)
#plt.show()                              # Display the plot.

from lucipy import LUCIDAC


hc = LUCIDAC()
hc.reset_circuit()
hc.set_circuit(f.generate(skip="/M1"))
hc.set_daq(num_channels=3)
hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
hc.set_op_time(ms=10)

from pylab import *
x, y, z = array(hc.start_run().data()).T

figure()
plot(y,z)
show()
