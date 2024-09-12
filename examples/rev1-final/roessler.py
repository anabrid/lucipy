#
# Roessler attractor on LUCIDAC:
#
# x' = -0.8y - 2.3z
# y' = 1.25x + 0.2y
# z' = 0.005 + 15z(x - 0.3796)
#

from lucipy import Circuit, Simulation, LUCIDAC, Route
from time import sleep
from lucipy.synchc import RemoteError

r = Circuit()                           # Create a circuit

x     = r.int(ic = .066)
my    = r.int()
mz    = r.int()
prod  = r.mul(id=1)
const = r.const(1)

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

r.probe(x, front_port=4)
r.probe(my, front_port=5)

r.measure(x)
r.measure(my)

hc = LUCIDAC()
hc.sock.sock.debug_print = True

hc.reset_circuit(dict(keep_calibration=False))

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})


# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k: v for k,v in r.generate().items() if not "/M1" in k }


# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
config["/0"]["/M1"]["calibration"] = {
    "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
    "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
    "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}

print(config)

hc.set_config(config)

hc.manual_mode("ic")
sleep(0.5)
hc.manual_mode("op")
