from lucipy import LUCIDAC, Circuit, Route
import matplotlib.pyplot as plt

def roessler(ode):
  x = ode.int(id=0, ic=-0.0666)
  y = ode.int(id=1, ic=0)
  z = ode.int(id=2, ic=0)
  
  routes = [
    Route(8,   0,   1.25, 9),
    Route(9,   1,  -0.8,  8),
    Route(10,  2, -2.3,   8),
    Route(9,   3,  0.4,   9),
    Route(4,   4, -0.005,10),
    Route(8,   5,  1.0,   0),
    Route(4,  14,  0.38,  0),
    Route(10, 15, 15.0,   1),
    Route(0,  16, -1.0,  10),
    Route(8,  8,   0.0,  9),
    Route(9,  9,   0.0,  9)
  ]
  return routes

# connect to osci
lucidac_ip = "192.168.150.127"

# connect to LUCIDAC and prep data
hc = LUCIDAC("tcp://" + lucidac_ip)

ode = Circuit()
ode.add(roessler(ode))
config = ode.generate()

hc.set_config(config)
hc.set_op_time(ms=1000)

hc.start_run()
