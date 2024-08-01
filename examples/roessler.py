#!/usr/bin/env python3

import sys, time
from pprint import pprint
sys.path.append("..") # use that lucipy in parent directory

from lucipy import LUCIDAC, Circuit, Route

ode = Circuit()

def roessler():
    x = ode.int(id=0, ic=-0.0666)
    y = ode.int(id=1, ic=0)
    z = ode.int(id=2, ic=0)
    
    routes = [
        Route(8,   0,   1.25, 9),
        Route(9,   1,  -0.8,  8),
        Route(10,  2, -2.3,   8),
        Route(9,   3,  0.2,   9), # Int1->Int1 Lit: 0.2, hier war: 0.4
        Route(4,   4, -0.005,10),
        Route(8,   5,  1.0,   0),
        Route(4,  14,  0.38,  0),
        Route(10, 15, 15.0,   1),
        Route(0,  16, -1.0,  10),
        
        Route(8,  8,   0.0,  9),
        Route(9,  9,   0.0,  9)
    ]
    return routes

# funktionsfaehig:
sinus_von_pybrid = \
    {'entity': None,
 'config': {'/0': {'/M0': {'elements': [{'ic': 0.709971666, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000}]},
   '/M1': {},
   '/U': {'outputs': [8,
     9,
     None,
     None,
     None,
     None,
     None,
     None,
     8,
     9,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None]},
   '/C': {'elements': [1.00024426,
     -1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426]},
   '/I': {'outputs': [None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     [1],
     [0],
     None,
     None,
     None,
     None,
     None,
     None]}}}}



def sinus():
    print("Sinus")
    hc.query("reset")
    #for i in range(8):
    #    ode.set_ic(el=i, val= (i+1) / 10)
    
    ode.set_ic(0, 0.7)
    
    routes_klappt = [
        Route(8, 0,  1.0, 9),
        Route(9, 1, -1.0, 8),
       # Route(8, 8,  0.0, 14),
        Route(9, 9,  0.0, 15),
    ]
        
    routes_falsch = [
        Route(8, 8,  1.0, 9),
        Route(9, 9, -1.0, 8)
    ]
    
    routes_klappt_vielleicht = [
        Route(8, 0,  1.0, 9),
        Route(9, 1, -1.0, 8),
        Route(8, 8,  1.0, 9),
        Route(9, 9, -1.0, 8),
    ]
    
    return routes_klappt_vielleicht

def constant():
    hc.query("reset")
    for i in range(8):
        ode.set_ic(el=i, val= (i+1) / 10)
    return [ Route(12, lane, 0.0, 4) for lane in range(32) ]


def f_roessler(t, s):
    x,y,z = s
    A,B,C = 0.2, 0.005, 0.3796
    X = -0.8*y - 2.3*z
    Y = 1.25*x + A*y
    Z = B + 15*z*(x-C)
    return [X, Y, Z]
   

ode.add(roessler())

if True:

    from lucipy.simulator import *
    from pylab import *
    ion()

    sim = simulation(ode)
    t_final=0.6
    ics = [0.5, 0.1, 0]
    interest = ["x", "y", "z"]

    res_luci = sim.solve_ivp(t_final, ics=ics, dense_output=True)
    res_py   = solve_ivp(f_roessler, t_span=[0, t_final], y0=ics, dense_output=True)
    
    data_luci = res_luci.sol(linspace(0,t_final,300))
    data_py =   res_py.sol(linspace(0,t_final,300))
    
    if False:
        data = data_py
        for i, label in enumerate(interest):
            plot(data[i], label=label)
        legend()
    else:
        subplot(2,1,1)
        for i,label in enumerate(interest):
            p = plot(data_py[i], label=f"{label} (Python)")
            plot(data_luci[i], "--", label=f"{label} (lucisim)", color=p[0].get_color(), alpha=0.7)
        legend()

        subplot(2,1,2)
        dydt = lambda F, res: np.array([F(t,y) for t,y in zip(res.t, res.y.T)]).T

        dyluci = dydt(sim.rhs, res_luci)
        dypy = dydt(f_roessler, res_py)

        for i,label in enumerate(interest):
            p = plot(dyluci[i], label=f"{label} (Python)")
            plot(dypy[i], "--", label=f"{label} (lucisim)", color=p[0].get_color(), alpha=0.7)
        legend()

if False:
    hc = LUCIDAC("tcp://192.168.150.127") # Frankfurt
    #hc = LUCIDAC("tcp://192.168.102.230") # ulm
    
    config = ode.generate()
    pprint(config)
    hc.set_config(config)


    manual_control = True
    if manual_control:
        hc.query("manual_mode", dict(to="ic"))
        time.sleep(1)
        hc.query("manual_mode", dict(to="op"))
        time.sleep(20)
        hc.query("manual_mode", dict(to="halt"))
    else:
        hc.set_op_time(ms=900)
        hc.start_run()
