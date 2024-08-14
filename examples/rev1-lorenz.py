# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

#lucidac_endpoint = "tcp://192.168.150.127" # Frankfurt
#lucidac_endpoint = "tcp://192.168.102.230" # Ulm

lorenz = Circuit()

x   = lorenz.int(ic=-1)
y   = lorenz.int()
z   = lorenz.int()
mxy = lorenz.mul()   # -x*y
xs  = lorenz.mul()   # +x*s
c   = lorenz.const()

lorenz.connect(x,  x, weight=-1)
lorenz.connect(y,  x, weight=+1.8) # auf LUCIDAC geht nur -1.8, in simulation nur +1.8. Math. korrekt ist +
  
lorenz.connect(x, mxy.a)
lorenz.connect(y, mxy.b)
  
lorenz.connect(mxy, z, weight=-1.5)
lorenz.connect(z,   z, weight=-0.2667)
  
lorenz.connect(x, xs.a, weight=-1)
lorenz.connect(z, xs.b, weight=+2.67)
lorenz.connect(c, xs.b, weight=-1)
  
lorenz.connect(xs, y, weight=-1.536)
lorenz.connect(y,  y, weight=-0.1)

print("Circuit routes for Lorenz attractor: ")
print(lorenz)

# filter out M1 because there is nothing to set
# and MCU complains if I try to configure something nonexisting
config = { k:v for k,v in lorenz.generate().items() if not "/M1" in k }

config["/U"]["outputs"] = [ (-1 if v == None else v) for v in config["/U"]["outputs"] ]

hc = LUCIDAC()
hc.query("reset_circuit")
hc.set_config(config)


# set all ACL channels to external
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
    "acl_select": [ "external" ]*8,
    "adc_channels": [ i0, i1 ],    
}})


manual_control = True

if manual_control:
    hc.manual_mode("ic")
    sleep(1)
    hc.manual_mode("op")
    sleep(20)
    hc.manual_mode("halt")
else:
    hc.set_daq(num_channels=2)
    nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
    hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

    run = hc.start_run()

