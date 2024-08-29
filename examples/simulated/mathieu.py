# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection

lucidac_endpoint = "tcp://192.168.150.127"

# useful values are a \in [0,1]
start_a = 4

circuit = Circuit()

x,y,dx,dy = circuit.ints(4)
circuit.set_ic(y, -0.1)

m = circuit.mul()
c = circuit.const()

circuit.connect(c, dx, weight=+2)
circuit.connect(x, dx, weight=+4)
circuit.connect(dx, x, weight=-1)
circuit.connect(x,  x, weight=-0.005) # damping for manual amplitude stabilization

param_route = circuit.connect(y, m.a, weight=-start_a/10)
do_couple = True
if do_couple:
    circuit.connect(x, m.b, weight=-1)
else:
    circuit.connect(c, m.b, weight=+1)

circuit.connect(m, dy, weight=-1)
circuit.connect(dy, y, weight=-2)

# dummy connections for external readout (ACL_OUT),
# will change in REV1 hardware 
circuit.add(Route(x.out, 8, 0, 6))
circuit.add(Route(y.out, 9, 0, 6))

print("Circuit routes for Mathieu's equation: ")
print(circuit)

hc = LUCIDAC(lucidac_endpoint)
hc.query("reset")
hc.set_config(circuit.generate())
hc.set_op_time(ms=1000)
hc.run_config.halt_on_overload = False

hc.start_run()

# to sweep throught the parameter space, it is enough to change
# the relevant potentiometer instead of reprogramming the whole circuit:
sweep_coeff = param_route.lane
#hc.set_by_path(["/C", "elements", str(sweep_coeff), "factor"], -2.0/10)

def run_with(a):
    hc.slurp()
    hc.set_config({ "C": { "elements": { str(sweep_coeff): -a/10 } }})
    hc.slurp()
    hc.start_run()
    hc.slurp()
