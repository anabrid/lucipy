from lucipy import LUCIDAC, Circuit, Route
from lucipy.simulator import simulation

ode = Circuit()

x = ode.int(id=0, ic=1)
y = ode.int(id=1, ic=0)
  
lane = 2
routes = [
    #Route(c.out,  coeff, -0.5,  x.a),
    Route(x.out,  0,     +0.5,  y.a),
    Route(y.out,  lane,  -0.5,  x.a),

    # view-only routes
    # keep in mind lane 8 is defective
    Route(x.out,  8,   0,  0),
    Route(y.out,  9,   0,  0),
]

ode.add(routes)

sim = simulation(ode)
print(f"{sim.nonzero()=}")

res = sim.solve_ivp(t_final=2)
print(res.y)
