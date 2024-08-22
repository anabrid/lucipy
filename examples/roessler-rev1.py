#
# Roessler attractor on LUCIDAC:
#
# x' = -0.8y - 2.3z
# y' = 1.25x + 0.2y
# z' = 0.005 + 15z(x - 0.3796)
#

from lucipy import Circuit, Simulation, LUCIDAC, Route
from time import sleep

r = Circuit()                           # Create a circuit

x     = r.int(ic = .066)
my    = r.int()
mz    = r.int()
prod  = r.mul()
const = r.const()

r.connect(my,    x, weight = -0.8)
r.connect(mz,    x, weight = -2.3)

r.connect(x,     my, weight = 1.25)
r.connect(my,    my, weight = -0.2)

r.connect(const, mz, weight = 0.005)
r.connect(prod,  mz, weight = 10)
r.connect(prod,  mz, weight = 5)

r.connect(mz,    prod.a, weight = -1)
r.connect(x,     prod.b)
r.connect(const, prod.b, weight = -0.3796)

sink = 12 # third Multiplier
acl_lane = 24
r.add( Route(x.out, acl_lane+5, 1.0, sink) )
r.add( Route(my.out, acl_lane+6, 1.0, sink) )

hc = LUCIDAC()

hc.reset_circuit()

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k: v for k,v in r.generate().items() if not "/M1" in k }

print(config)

hc.set_config(config)

manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(0.5)
    hc.manual_mode("op")
    #sleep(0.5)
else:
    hc.set_daq(num_channels=2, sample_rate=125_000)
    nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

    run = hc.start_run()
