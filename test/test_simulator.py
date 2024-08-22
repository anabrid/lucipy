from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation, Emulation

def circuit_constant2acl_out(coeff0 = -0.5, coeff1 = +0.5):
    # provides a circuit which puts constants onto ACL_OUT
    
    # check whether constants follow this mental picture: 
    #
    #
    # | clanes | U lanes[0:15] | U lanes [16:31]
    # | ------ | ------        | -----     
    # | 14     |  Mblock out   | CONSTANTS
    # | 15     |  CONSTANTS    | Mblock out
    #
    
    const = Circuit()
    const.use_constant()
    
    # we can only directly probe a constant on ACL_OUT...

    sink = 0 # some integrator, don't care
    acl_begin = 24
    
    const.add( Route(14, acl_begin+0, coeff0, sink) ) # this must     work
    const.add( Route(15, acl_begin+1, coeff1, sink) ) # this must not work
    
    return const

def test_constant_circuit():
    config = circuit_constant2acl_out().generate()
    print(config)
    assert "constant" in config["/U"]
    assert config["/U"]["constant"] == True
    

def test_constant_detection_in_simulation():
    const = Circuit()
    const.use_constant()
    # constant from clane=14 -> DO end up in 16<=lanes<32
    # constant from clane=15 -> DO end up in  0<=lanes<16
    const.add( Route(14, 0, 0.1, 0) ) # must work
    const.add( Route(14,16, 0.2, 1) ) # must not work
    const.add( Route(15,17, 0.3, 2) ) # must work
    const.add( Route(15, 2, 0.4, 1) ) # must not work
    sim = Simulation(const)
    assert all(sim.constant[0:4] == [0.1, 0, 0.3, 0 ])
    
def do_NOT_YET_test_measure_acl_constant():
    coeff0 = -0.5
    coeff1 = +0.5
    
    sim = Simulation(circuit_constant2acl_out(coeff0, coeff1))
    irrelevant_state = [0.]*8
    acl_outs = sim.acl_out_values(irrelevant_state)
    assert acl_outs[0] == coeff0
    assert acl_outs[1] != coeff1

def test_ramp():
    # This circuit uses the constant giver for integrating over a constant
    
    ic = +1
    slope = -1
    t_final = 2
    expected_result = -t_final*slope - ic
    assert expected_result == +1

    ramp = Circuit()
    i = ramp.int()
    assert i.out == 0
    
    c = ramp.const()
    assert c.out == 14
    
    ramp.connect(c, i, weight=slope)
    ramp.set_ic(0, ic)
    
    sim = Simulation(ramp)
    assert sim.constant[0] == slope
    assert all(sim.constant[1:] == 0)
    
    res = sim.solve_ivp(2)
    
    assert res.y[0, 0] == -ic
    
    import numpy as np
    assert np.isclose(res.y[0,-1], expected_result)

