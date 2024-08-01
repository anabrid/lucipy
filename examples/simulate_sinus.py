from lucipy import LUCIDAC, Circuit, Route
from lucipy.simulator import simulation
from time import sleep

ode = Circuit()

x = ode.int(id=0, ic=1)
y = ode.int(id=1, ic=0)
z = ode.int(id=2, ic=0)
c = ode.const()
m0 = ode.mul()
m1 = ode.mul()
m2 = ode.mul()

routes = [
    #Route(c.out,  coeff, -0.5,  x.a),
    
    Route(x.out,  0,    +0.5,  y.a),
    Route(y.out,  1,    -0.5,  x.a),
    
#    Route(c.out,  2,   -1.0, m0.a),
#    Route(x.out,  3,    1.0, m0.b),
    
#    Route(c.out,  4,   -1.0, m1.a),
#    Route(m0.out, 5,    1.0, m1.b),
    
#    Route(m1.out, 6,   +0.5, y.a),
    
#    Route(m1.out, 7,  -1.0, m2.a),
#    Route(x.out,  8,   1.0, m2.b),
#    Route(m2.out, 9,   1.0, z.a),

    # view-only routes
    # keep in mind lane 8 is defective
    Route(x.out,  8,   0,  0),
    Route(y.out,  9,   0,  0),
]

ode.add(routes)

if False:
    sim = simulation(ode)
    print(f"{sim.nonzero()=}")

    res = sim.solve_ivp(t_final=12, dense_output=True)

    from pylab import *

    ion()
    x,y,z, *others = res.sol(linspace(0,12))
    plot(x)
    plot(y)
    plot(z)

#lucidac_endpoint = "tcp://192.168.150.127" # Frankfurt
lucidac_endpoint = "tcp://192.168.102.230" # Ulm

hc = LUCIDAC(lucidac_endpoint)
hc.query("reset")
hc.set_config(ode.generate())

manual_control = True
if manual_control:
    hc.query("manual_mode", dict(to="ic"))
    sleep(1)
    hc.query("manual_mode", dict(to="op"))
    sleep(20)
    hc.query("manual_mode", dict(to="halt"))
else:
    hc.set_op_time(ms=1000)
    hc.run_config.halt_on_overload = False

    hc.start_run()

