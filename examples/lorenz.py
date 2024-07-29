# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection

lucidac_endpoint = "tcp://192.168.150.127"

lorenz = Circuit()

x   = lorenz.int(ic=-1)
y   = lorenz.int()
z   = lorenz.int()
mxy = lorenz.mul()   # -x*y
xs  = lorenz.mul()   # +x*s
c   = lorenz.const()

lorenz.connect(x,  x, weight=-1)
lorenz.connect(y,  x, weight=-1.8)
  
lorenz.connect(x, mxy.a)
lorenz.connect(y, mxy.b)
  
lorenz.connect(mxy, z, weight=-1.5)
lorenz.connect(z,   z, weight=-0.2667)
  
lorenz.connect(x, xs.a, weight=-1)
lorenz.connect(z, xs.b, weight=+2.67)
lorenz.connect(c, xs.b, weight=-1)
  
lorenz.connect(xs, y, weight=-1.536)
lorenz.connect(y,  y, weight=-0.1)
  
# dummy connections for external readout (ACL_OUT),
# will change in REV1 hardware 
lorenz.add(Route(x.out, 8, 0, 6))
lorenz.add(Route(y.out, 9, 0, 6))

print("Circuit routes for Lorenz attractor: ")
print(lorenz)

hc = LUCIDAC(lucidac_endpoint)
hc.query("reset")
hc.set_config(lorenz.generate())
hc.set_op_time(ms=1000)
hc.run_config.halt_on_overload = False

hc.start_run()
