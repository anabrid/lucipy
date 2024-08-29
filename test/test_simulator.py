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
