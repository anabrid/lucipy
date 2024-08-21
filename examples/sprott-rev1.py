from lucipy import Circuit, Simulation, LUCIDAC, Route
from lucipy.circuits import Mul
import matplotlib.pyplot as plt
import numpy as np
from time import sleep

#
# Sprott on REV1 Hardware
#

alpha = 1.7

sprott = Circuit()

# use manual clane positions as the int and mul calls
# currently give the wrong indices.

# REV1 M0 = Mint
# REV1 M1 = MMul

mx      = 0 #sprott.int(ic = .1)
my      = 1 #sprott.int()
mz      = 2# sprott.int()
# Mul = namedtuple("Mul", ["id", "out", "a", "b"])
mxy    = Mul(0, 8, 8,   9) # sprott.mul()
yz     = Mul(1, 9, 10, 11) #sprott.mul()

# set ICs
sprott.set_ic(mx, .1)

# use constant at lane 24
sprott.use_constant()
const_clane  = 14 # constant at clane 14 and 15<lane<32  #sprott.const()
const_lane   = 16


acl_lane = 24 # first ACL lane

sprott.connect(yz, mx, weight = 10)         # x' = yz

sprott.connect(mx, my, weight = -1)         # y' = x - y
sprott.connect(my, my)
sprott.add( Route(const_clane, acl_lane+5, 0.1, mz) )      # z' = 1 - xy (scaled!)
sprott.connect(mxy, mz, weight = 10)

sprott.connect(mx, mxy.a)                   # -xy
sprott.connect(my, mxy.b, weight = -1)

sprott.connect(my, yz.a)                    # yz
sprott.connect(mz, yz.b)


sink = 12 # third Multiplier

sprott.add( Route(mx, acl_lane+6, 1.0, sink) )
sprott.add( Route(my, acl_lane+7, 1.0, sink) )

hc = LUCIDAC()

hc.reset_circuit()

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k: v for k,v in sprott.generate().items() if not "/M1" in k }

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
