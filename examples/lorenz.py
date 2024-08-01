# Implement Lorentz attractor as in 
# https://analogparadigm.com/downloads/alpaca_2.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection
from time import sleep

#lucidac_endpoint = "tcp://192.168.150.127" # Frankfurt
lucidac_endpoint = "tcp://192.168.102.230" # Ulm


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
  
# dummy connections for external readout (ACL_OUT),
# will change in REV1 hardware 
lorenz.add(Route(x.out, 8, 0, 6))
lorenz.add(Route(y.out, 9, 0, 6))

def f_lorenz(t, s):
    x,y,z = s
    X = 1.8*y - x
    Z = 1.5*x*y - 0.2667*z
    S = -(1-2.68*z)
    R = -x*S
    Y = 1.536*R - 0.1*y
    return [X,Y,Z]

print("Circuit routes for Lorenz attractor: ")
print(lorenz)

from lucipy.simulator import *

sim= simulation(lorenz)
print(f"{sim.nonzero()=}")

t_final=50
res_luci = sim.solve_ivp(t_final, ics=[0,1,1.05], dense_output=True)
res_py = solve_ivp(f_lorenz, [0,t_final], [0,1,1.05], dense_output=True)


from pylab import *

ion()
interest = ["x", "y", "z"]
data_luci = res_luci.sol(linspace(0,t_final,300))
data_py =   res_py.sol(linspace(0,t_final,300))

subplot(2,1,1)
for i,label in enumerate(interest):
    p = plot(data_py[i], label=f"{label} (Python)")
    plot(data_luci[i], "--", label=f"{label} (lucisim)", color=p[0].get_color(), alpha=0.7)
legend()

subplot(2,1,2)
dydt = lambda F, res: np.array([F(t,y) for t,y in zip(res.t, res.y.T)]).T

dyluci = dydt(sim.rhs, res_luci)
dypy = dydt(f_lorenz, res_py)

for i,label in enumerate(interest):
    p = plot(dyluci[i], label=f"{label} (Python)")
    plot(dypy[i], "--", label=f"{label} (lucisim)", color=p[0].get_color(), alpha=0.7)
legend()



if True:
    hc = LUCIDAC(lucidac_endpoint)
    hc.query("reset")
    hc.set_config(lorenz.generate())

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

