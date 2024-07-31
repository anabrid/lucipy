# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection
from time import sleep

lucidac_endpoint = "tcp://192.168.150.127"

neuron = Circuit()

i0 = neuron.int(ic=+1, slow=False)
i1 = neuron.int(ic=-1, slow=False)
i2 = neuron.int(ic=+1, slow=True)
m0 = neuron.mul()
m1 = neuron.mul()
c  = neuron.const()

slow = 1/10

neuron.connect(m1, i0,  weight=+4*slow)
neuron.connect(m0, i0,  weight=-6*slow)
neuron.connect(c,  i0,  weight=+1*slow)
neuron.connect(i1, i0,  weight=-7.5*slow)
if True:
    neuron.connect(i2, i0,  weight=-1*slow)

if True:
    neuron.connect(i0, i2,  weight=+0.4*slow)
    neuron.connect(c,  i2,  weight=+0.32*slow)
neuron.connect(i2, i2,  weight=-0.1*slow)

neuron.connect(i0, m0.a, weight=+1)
neuron.connect(i0, m0.b, weight=+1)

neuron.connect(m0, m1.a, weight=+1)
neuron.connect(i0, m1.b, weight=+1)

neuron.connect(m0, i1,   weight=-1.33*slow)
neuron.connect(c,  i1,   weight=-0.066*slow)
neuron.connect(i1, i1,   weight=-1*slow)

# dummy connections for external readout (ACL_OUT),
# will change in REV1 hardware 
neuron.add(Route(i0.out, 8, 0, 6))
neuron.add(Route(i1.out, 9, 0, 6))

print("Circuit routes for Hindmarsh-Rose single Neuron model: ")
print(neuron)

hc = LUCIDAC(lucidac_endpoint)
hc.query("reset")
hc.set_config(neuron.generate())

Use_FlexIO = False
if Use_FlexIO:

    hc.set_op_time(ms=1000)

    # TODO should be determined automatically
    # TODO 10_000_000 does not work
    hc.run_config.ic_time = 200_000

    hc.run_config.halt_on_overload = False

    hc.start_run()

else:
    # manual control because IC/OP times are not working

    hc.query("manual_mode", dict(to="ic"))
    sleep(1)
    hc.query("manual_mode", dict(to="op"))
    sleep(3)
    hc.query("manual_mode", dict(to="halt"))

