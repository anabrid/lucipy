#
# Unit tests for the circuits package
#


from fixture_circuits import circuit_constant2acl_out

def test_constant_circuit():
    carrier = circuit_constant2acl_out().generate()
    assert "/0" in carrier
    assert "constant" in carrier["/0"]["/U"]
    assert carrier["/0"]["/U"]["constant"] == True
    
