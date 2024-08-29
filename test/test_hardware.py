#
# This kind of tests should go against the emulator the same way as against real hardware.#
# Well now at least this file goes against real hardware
#
# Running tests in this file requires the environment variable LUCIDAC_ENDPOINT
# set to a suitable value, for instance "tcp://192.168.150.229:5732"
#

import pytest
import os

from lucipy import LUCIDAC, Circuit, Simulation
from lucipy.simulator import remove_trailing

from fixture_circuits import circuit_sinus, measure_ramp

from itertools import product
import numpy as np

def requires_hardware(f):
    return pytest.mark.skipif(
        not "LUCIDAC_ENDPOINT" in os.environ,
        reason=f"Hardware tests require env var LUCIDAC_ENDPOINT"
    )(f)

@pytest.fixture
def hc():
    hc = LUCIDAC()
    hc.reset_circuit()
    yield hc
    hc.sock.sock.close() # or similar

# tests the protocol and configuration readout
@requires_hardware
def test_set_circuit_for_cluster(hc):
    set_conf_cluster = circuit_sinus().generate(skip="/M1") # Test Hardware has no M1!)
    hc.set_circuit(set_conf_cluster)
    get_conf_cluster = hc.get_circuit()["config"]
           
    # canonicalize I block defaults:
    for i,v in enumerate(get_conf_cluster["/0"]["/I"]["outputs"]):
        if not v:
            get_conf_cluster["/0"]["/I"]["outputs"][i] = []
    
    # get rid of M1 block
    del get_conf_cluster["/0"]["/M1"]
            
    print(f"{set_conf_cluster['/0']=}")
    print(f"{get_conf_cluster['/0']=}")
    
    ## Differences are still in the U-block. Look carefully.
    ## Probably we have an old an unsuitable commit.
    
    assert set_conf_cluster["/0"] == get_conf_cluster["/0"]

# tests the protocol and configuration readout
@requires_hardware
def test_set_adc_channels(hc):
    c = Circuit()
    c.set_adc_channels([0,1,2])
    set_conf = c.generate(skip="/M1")  # Test Hardware has no M1!
    print(f"{set_conf=}")
    hc.set_config(set_conf)
    get_conf = hc.get_circuit()["config"]
    
    # canonicalize: Remove trailing "None"
    get_adc_channels = remove_trailing(get_conf["adc_channels"])    
    
    print(f"{get_conf=}")
    print(f"{get_adc_channels=}")
    assert get_adc_channels == c.adc_channels

@requires_hardware
@pytest.mark.parametrize("slope,lane", product([+1,-1], range(32)))
def SKIP_test_ramp(hc, slope, lane):
    valid_endpoint, valid_evolution == measure_ramp(slope, lane) # const_value=-1
    assert valid_endpoint
    assert valid_evolution

   

# TESTs to add:
#
#
#  1) Very short runtime: daq
#  2) Very long runtime: daq
