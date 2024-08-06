# Implement Hindmarsh-Rose-model of a single spiking neuron
# https://analogparadigm.com/downloads/alpaca_28.pdf

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep

lucidac_endpoint = "tcp://192.168.150.127" # frankfurt
#lucidac_endpoint = "tcp://192.168.102.230" # ulm

neuron = Circuit()

i0 = neuron.int(ic=-1, slow=False)
i1 = neuron.int(ic=+1, slow=False)
i2 = neuron.int(ic=-1, slow=True)
m0 = neuron.mul()
m1 = neuron.mul()
c  = neuron.const()

slow = 1/10
slow = 1

neuron.connect(m1, i0,  weight=-4*slow)
neuron.connect(m0, i0,  weight=-6*slow)
neuron.connect(c,  i0,  weight=1)
neuron.connect(i1, i0,  weight=+7.5*slow)
neuron.connect(i2, i0,  weight=-1*slow)

neuron.connect(i0, i2,  weight=+0.4*slow)
neuron.connect(c,  i2,  weight=+0.32*slow)
neuron.connect(i2, i2,  weight=-0.1*slow)

neuron.connect(i0, m0.a, weight=+1)
neuron.connect(i0, m0.b, weight=+1)

neuron.connect(m0, m1.a, weight=+1)
neuron.connect(i0, m1.b, weight=+1)

neuron.connect(m0, i1,   weight=+1.33*slow)
neuron.connect(c,  i1,   weight=+0.066*slow)
neuron.connect(i1, i1,   weight=-1*slow)

# dummy connections for external readout (ACL_OUT),
# will change in REV1 hardware 
neuron.add(Route(i1.out, 8, 0, 6))
neuron.add(Route(i2.out, 9, 0, 6))

print("Circuit routes for Hindmarsh-Rose single Neuron model: ")
print(neuron)


def f_neuron(t, s):
    # this model spikes with t_final=3000, ics = [1, 0.2, 0], rest solve_ivp defaults
    x, y, z = s
    a, b, c, d, r, s, xr, Iext = 1, 3, 1, 5, 1e-3, 4, -8./5., 1. + 0.3
    dx = -a*x**3 + b*x**2 + y - z + Iext
    dy = -d*x**2 + c - y
    dz = r*(s*(x-xr) - z)
    return [dx, dy, dz]

def f_scaled(t,s):
    x,y,z = s
    k0z = 1/100
    dx = -4*x**3 + 6*x**2 + 7.5*y - z + 1.0
    dy = -1.33*x**2 - y + 0.066
    dz = 0.4*x - 0.1*z + 0.32
    return [dx,dy,k0z*dz]


xyz = list("xyz")
eqs = neuron.to_sympy(xyz, subst_mul=True, no_func_t=True)
print(eqs)
from sympy import latex, lambdify, symbols
print(latex(eqs))

rhs = [ e.rhs for e in eqs ]
rhs[2] *= 1/100 # slower k0z
x,y,z = symbols(xyz)

f_scipy = lambdify((x,y,z), rhs)



if True:

    from scipy.integrate import solve_ivp
    from pylab import *
    ion()

    sim = Simulation(neuron)
    t_final=1000
    ics = [0.5, 0.1, 0]
    ics = [1, -1, +1]
    #ics = sim.ics[0:3]
    #ics = [2,2,2]
    #ics = [1, 0.2, 0] # max_step=0.01, spikes for around t=500
   
    scaling = [ 1/2, 1/2, 1/15 ]
    
    #ics = array(ics)

    interest = ["x", "y", "z"]

    res_luci = sim.solve_ivp(t_final, clip=False, ics=ics, dense_output=False)
    #res_luci = solve_ivp(lambda t,s: f_scipy(*s), t_span=[0, t_final], y0=ics)
    res_py   = solve_ivp(lambda t,s: f_scipy(*s), t_span=[0, t_final], y0=ics, dense_output=False)
    #res_py   = solve_ivp(f_scaled, t_span=[0, t_final], y0=ics, dense_output=False)
    #res_scpy = solve_ivp(f_scaled, t_span=[0, t_final], y0=ics, dense_output=False)
    
    data_luci = res_luci.y #res_luci.sol(linspace(0,t_final,300))
    data_py =   res_py.y # res_py.sol(linspace(0,t_final,300))
    #data_py = res_py.y
    #data_scpy = res_scpy.y
    
    if False:
        data = data_luci
        for i, label in enumerate(interest):
            plot(data[i], label=label)
        legend()
    else:
        for i,label in enumerate(interest):
            subplot(2,1,1)
            p = plot(data_py[i], label=f"{label} (Python)")
            legend()
            subplot(2,1,2)
            #p = plot(data_scpy[i], label=f"{label} (Scaled Python)")
            plot(data_luci[i], label=f"{label} (lucisim)", color=p[0].get_color())
            legend()
        #ylim(-20,20)

        
        if False:
            dydt = lambda F, res: np.array([F(t,y) for t,y in zip(res.t, res.y.T)]).T

            dyluci = dydt(sim.rhs, res_luci)
            dypy = dydt(f_neuron, res_py)

            for i,label in enumerate(interest):
                p = plot(res_py.t, dypy[i], label=f"{label} (Python)")
                plot(res_luci.t, dyluci[i], "--", label=f"{label} (lucisim)", color=p[0].get_color(), alpha=0.7)
            legend()

if True:
    hc = LUCIDAC(lucidac_endpoint)
    hc.query("reset")
    hc.set_config(neuron.generate())

    Use_FlexIO = False
    if Use_FlexIO:

        hc.set_op_time(ms=1000)

        # TODO should be determined automatically
        # TODO 10_000_000 does not work
        hc.run_config.ic_time = 200_000

        hc.run_config.halt_on_overload = False

        hc.start_run()

    else:
        # manual control because IC/OP times are not working

        print("IC")
        hc.query("manual_mode", dict(to="ic"))
        sleep(1)
        print("OP")
        hc.query("manual_mode", dict(to="op"))
        sleep(3)
        print("HALT")
        hc.query("manual_mode", dict(to="halt"))

