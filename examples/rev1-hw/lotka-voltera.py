#
# Hunter Prey population dynamics (Lotka-Volterra system)
#

from lucipy import Circuit, LUCIDAC
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

lv.measure(h)
lv.measure(l)

emu = LUCIDAC("emu://")
real = LUCIDAC()  # use environment variable for connection

#### obtain results from REAL device

hc = real
hc.reset_circuit(dict(keep_calibration=False))

hc.set_by_path(["0", "SH"], {"state": "TRACK"})
hc.set_by_path(["0", "SH"], {"state": "INJECT"})

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k: v for k,v in lv.generate().items() if not "/M1" in k }

# These values come from manual calibration by BU and SK at 2024-09-10 for REV1@FFM.
config["/0"]["/M1"]["calibration"] = {
    "offset_x": [ 0.0,   -0.003, -0.007,  -0.005], # !!! offset_x = input B !!!
    "offset_y": [ 0.1,    0.0,    0.003,   0.0  ], # !!! offset_y = input A !!!
    "offset_z": [-0.038, -0.033, -0.0317, -0.033]
}

hc.run_config.streaming = False
hc.run_config.calibrate = False

t_final=13
hc.set_circuit(config)
hc.set_op_time(ms=t_final)
l,v = np.array(hc.start_run().data()).T
t = np.linspace(0, t_final, num=len(l))

t_hw, l_hw,  v_hw  = t,l,v



#### obtain simulated

def run_lv(hc):
    t_final=13
    hc.set_circuit(lv)
    hc.set_op_time(ms=t_final)
    l,v = np.array(hc.start_run().data()).T
    t = np.linspace(0, t_final, num=len(l))
    return t,l,v
    
t_emu, l_emu, v_emu = run_lv(emu)
#_, l_hw,  v_hw  = run_lv(real)

plot_l = plt.plot(t_emu, l_emu, "--")
plt.plot(t_hw, l_hw, color=plot_l[0].get_color())
plot_t = plt.plot(t_emu, v_emu, "--")
plt.plot(t_hw, v_hw, color=plot_t[0].get_color())
plt.show()                                  # Display the plot.

