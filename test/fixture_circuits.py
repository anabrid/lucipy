from lucipy import Circuit, Route, Connection

# This file contains *simple* circuits which can be well tested automatically

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

def sinus():
    i0, i1 = 0, 1
    rev1 = Circuit()
    
    #rev1.set_ic(i0, +1)
    #rev1.set_ic(i1, 0)
    
    rev1.int(id=i0, ic=+1, slow=False)
    rev1.int(id=i1, ic=0, slow=False)
    
    rev1.add( Route(i0, 2,  1, i1) )
    rev1.add( Route(i1, 3, -1,  i0) )

    acl_lane = 24 # first ACL lane
    rev1.add( Route(i0, acl_lane, 1.0, i0) )
    rev1.add( Route(i1, acl_lane+1, 1.0, i0) )
    
    return rev1


sin = sinus()
sinconf = sin.generate()
print(sin)
print(sinconf)
cos = Circuit()
cos.load(sinconf)
print(cos)
