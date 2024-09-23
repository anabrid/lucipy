from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

eta = 4    # tunes the nonlinearity, value 0 results in an harmonic oscillator

vdp = Circuit()

mdy = vdp.int()
y   = vdp.int(ic = 0.1)
y2  = vdp.mul()
fb  = vdp.mul(2)
c   = vdp.const()

vdp.connect(fb, mdy, weight = -eta)
vdp.connect(y,  mdy, weight = -0.5)

vdp.connect(mdy, y, weight = 2)

vdp.connect(y, y2.a)
vdp.connect(y, y2.b)

vdp.connect(y2,  fb.a, weight = -1)
vdp.connect(c,   fb.a, weight = 0.25)
vdp.connect(mdy, fb.b)

vdp.probe(mdy, front_port=5)
vdp.probe(y,   front_port=6)

vdp.measure(mdy) # register variables for internal DAQ
vdp.measure(y)   # up to eight variables/channels can be registered

hc = LUCIDAC()
hc.set_circuit(vdp)

run = hc.run(ic_time_us=200, op_time_ms=6)
data = np.array(run.data())

time = np.linspace(0, 6, num=data.shape[0])
plt.title("LUCIDAC-internal data aquisition: Van-der-Pol oscillator")
plt.plot(time, data[:,0], label="-$\dot y$")
plt.plot(time, data[:,1], label="$y$")
plt.axhline(0, color="black")
plt.xlabel("Time [ms]")
plt.legend()
plt.show()
