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
    
    const.add( Route(14, acl_begin+0, coeff0, sink) )
    const.add( Route(15, acl_begin+1, coeff1, sink) )
    
    return const

def test_constant_circuit():
    config = circuit_constant2acl_out().generate()
    print(config)
    assert "constant" in config["/U"]
    assert config["/U"]["constant"] == True
    
def test_measure_constant():
    coeff0 = -0.5
    coeff1 = +0.5
    
    sim = Simulation(circuit_constant2acl_out(coeff0, coeff1))
    irrelevant_state = [0.]*8
    acl_outs = sim.acl_out_values(irrelevant_state)
    assert acl_outs[0] == coeff0
    assert acl_outs[1] == coeff1

def circuit_ramp_ints():
    # This circuit divides an integrator by itself... well if that was possible
    pass

def circuit_ramp():
    # This circuit uses the constant giver for integrating over a constant
    
    # M0 = M-Block INT
    # M1 = M-Block MUL

    ### attention, do not use rev1.int() and friends as this is still
    ###     in REV0 numeration (where M1 and M0 are swapped)

    ramp = Circuit()
    ramp.add( Route(15, 0, -1.0, 0) ) # const input to int
    ramp.set_ic(0, +1)

    acl_lane = 24 # first ACL lane
    ramp.add( Route(0,  acl_lane, 1.0, 10) ) # 10 is just a sink
    
    i0 = 0
    rev1 = Circuit()
    rev1.set_ic(i0, +1)
    rev1.int(id=i0, ic=+1, slow=False)
    rev1.add( Route(i1, 3, -0.5,  i0) )

    acl_lane = 24 # first ACL lane
    rev1.add( Route(i0, acl_lane, 1.0, i0) )
    rev1.add( Route(i1, acl_lane+1, 1.0, i0) )
    
    return rev1.generate()


    # set all ACL channels to external
    hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
        "acl_select": [ "external" ]*8,
        "adc_channels": [ 0 ],
    }})

