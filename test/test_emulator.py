from lucipy import Emulation, Circuit, Route

def sinus():
    i0, i1 = 0, 1
    rev1 = Circuit()
    
    #rev1.set_ic(i0, +1)
    #rev1.set_ic(i1, 0)
    
    rev1.int(id=i0, ic=+1, slow=False)
    rev1.int(id=i1, ic=0, slow=False)
    
    rev1.add( Route(i0, 2,  0.25, i1) )
    rev1.add( Route(i1, 3, -0.5,  i0) )

    acl_lane = 24 # first ACL lane
    rev1.add( Route(i0, acl_lane, 1.0, i0) )
    rev1.add( Route(i1, acl_lane+1, 1.0, i0) )
    
    return rev1.generate()

def emulator():
    hc = Emulation()
    
    hc.mac = "foobar"
    hc.reset_circuit()
    return hc

def test_mac():
    hc = emulator()
    assert list(hc.get_entities()["entities"].keys())[0] == hc.mac

def test_config():
    hc = emulator()
    config = sinus()
    
    hc.set_circuit([hc.mac, "/0"], config)
    assert hc.get_circuit()["config"]["/0"] == config

