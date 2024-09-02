import pytest
from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation, Emulation
from fixture_circuits import circuit_constant2acl_out

def test_constant_detection_in_simulation():
    const = Circuit()
    const.use_constant()
    # constant from clane=14 -> DO end up in 16<=lanes<32
    # constant from clane=15 -> DO end up in  0<=lanes<16
    const.add( Route(14, 0, 0.1, 0) ) # must not work
    const.add( Route(14,16, 0.2, 1) ) # must work
    const.add( Route(15,17, 0.3, 2) ) # must not work
    const.add( Route(15, 2, 0.4, 3) ) # must work
    sim = Simulation(const)
    print(sim.constant)
    assert all(sim.constant[0:4] == [ 0., 0.2, 0., 0.4])
    
def do_NOT_YET_test_measure_acl_constant():
    coeff0 = -0.5
    coeff1 = +0.5
    
    sim = Simulation(circuit_constant2acl_out(coeff0, coeff1))
    irrelevant_state = [0.]*8
    acl_outs = sim.acl_out_values(irrelevant_state)
    assert acl_outs[0] == coeff0
    assert acl_outs[1] != coeff1

def test_integrator_chain():
    c = Circuit()
    i = c.ints(7)
    cnst = c.const()
    c.connect(cnst, i[0], weight=-1)
    for k in range(6):
        c.connect(i[k], i[k+1], weight=-(k+2))
    res = Simulation(c).solve_ivp(1, dense_output=True)
    
    import numpy as np
    tfine = np.linspace(0, 1)
    for k in range(7):
        # final one was reached
        assert np.isclose(res.y[k][-1], 1, atol=1e-3)
        # on coarse support points. When plotted with option "o-"
        # this looks weird because of the few support points.
        assert np.allclose(res.t**(k+1), res.y[k], atol=1e-3)
        # on a finer one which looks, when plotted, more like the solution
        assert np.allclose(tfine**(k+1), res.sol(tfine)[k], atol=1e-3)
        # (note, bigger tolerance is needed for bigger k)

def test_multipliers():
    c = Circuit()
    it = c.int() # integrates a "time"
    m1, m2, m3 = c.muls(3)
    cnst = c.const()
    
    a, b = 0.3, -0.25
    ab = a*b
    
    c.connect(cnst, it, weight=-1)
    
    # m1 = const * const
    c.connect(cnst, m1.a, weight=a)
    c.connect(cnst, m1.b, weight=b)
    
    # m2 = t * const
    c.connect(cnst, m2.a, weight=a)
    c.connect(it, m2.b)
    
    # m3 = t * t
    c.connect(it, m3.a)
    c.connect(it, m3.b)
    
    sim = Simulation(c)
    res = sim.solve_ivp(1, dense_output=True)
    # res.y holds integrator values in shape (num_integrators, num_timesteps)
    
    import numpy as np
    resm = np.array([sim.Mul_out(yt) for yt in res.y.T]).T
    # resm is the same shape (num_multipliers, num_timesteps)
    
    assert np.allclose(res.t, res.y[0]), "time ramp not properly integrated"
    assert np.allclose(resm[0], ab) # m1
    assert np.allclose(resm[1], a * res.t) # m2
    assert np.allclose(resm[2], res.t * res.t) # m3
    
    # can do the same also on "more continous" time
    tfine = np.linspace(0,1)
    resfine = res.sol(tfine)
    resmfine = np.array([sim.Mul_out(ytf) for ytf in resfine.T]).T
    
    assert np.allclose(tfine, resfine[0])
    assert np.allclose(resmfine[0], ab) # m1
    assert np.allclose(resmfine[1], a * tfine) # m2
    assert np.allclose(resmfine[2], tfine * tfine) # m3

@pytest.mark.parametrize("slow", [False, True])
def test_ramp(slow):
    # This circuit uses the constant giver for integrating over a constant
    # if slow, will use slow integrator.
    
    slow_factor = 100 if slow else 1 # difference between k0fast and k0slow
    
    ic = +1
    slope = -1
    t_final = 2 * slow_factor
    expected_result = -t_final * slope/slow_factor - ic
    assert expected_result == +1

    ramp = Circuit()
    i = ramp.int()
    assert i.out == 0
    
    c = ramp.const()
    assert c.out == 14
    
    ramp.connect(c, i, weight=slope)
    ramp.set_ic(0, ic)
    ramp.set_k0_slow(0, slow)
    
    sim = Simulation(ramp)
    assert sim.constant[0] == slope
    assert all(sim.constant[1:] == 0)
    
    res = sim.solve_ivp(t_final)
    
    assert res.y[0, 0] == -ic
    
    import numpy as np
    assert np.isclose(res.y[0,-1], expected_result)
