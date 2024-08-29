import pytest, numpy as np
from lucipy import LUCIDAC, Emulation, Circuit, Route

from fixture_circuits import circuit_sinus, measure_ramp

@pytest.fixture
def endpoint():
    emu = Emulation("127.0.0.1", 0)
    proc = emu.serve_forking()
    endpoint = emu.endpoint()
    yield endpoint
    proc.terminate()

def local_emulator():
    hc = Emulation()
    
    hc.mac = "foobar"
    hc.reset_circuit()
    return hc

def test_local_mac():
    hc = local_emulator()
    # Without going over TCP, the call returns the whole message
    assert list(hc.get_entities()["entities"].keys())[0] == hc.mac
    
def test_mac(endpoint):
    remote = LUCIDAC(endpoint)
    # The LUCIDAC API unwraps the message, returns only the useful payload
    assert list(remote.get_entities().keys())[0]  == Emulation().mac

def test_local_config():
    hc = local_emulator()
    config = circuit_sinus().generate()
    
    hc.set_circuit([hc.mac, "/0"], config)
    assert hc.get_circuit()["config"]["/0"] == config


def test_set_circuit_cluster(endpoint):
    hc = LUCIDAC(endpoint)
    set_conf_carrier = circuit_sinus().generate()
    hc.set_circuit(set_conf_carrier)
    get_conf_carrier = hc.get_circuit()["config"]

    assert "/0" in set_conf_carrier
    set_conf_cluster = set_conf_carrier["/0"]
    
    assert "/0" in get_conf_carrier
    get_conf_cluster = get_conf_carrier["/0"]
    
    print(f"{set_conf_cluster=}")
    print(f"{get_conf_cluster=}")
    assert set_conf_cluster == get_conf_cluster

def test_set_adc_channels(endpoint):
    hc = LUCIDAC(endpoint)
    c = Circuit()
    c.set_adc_channels([0,1,2])
    set_conf = c.generate()
    print(f"{set_conf=}")
    hc.set_config(set_conf)
    get_conf = hc.get_circuit()["config"]
    print(f"{get_conf=}")
    assert get_conf["adc_channels"] == c.adc_channels

def test_run_daq(endpoint):
    """
    This is a standalone test which makes sure the emulated data aquisition
    spills out the correct number of samples. This basically emulates how the
    FlexIO/DMA code should work. It also tests whether the result matches what
    is expected.
    """
    hc = LUCIDAC(endpoint)
    hc.reset_circuit()
    
    sinus = Circuit()
    
    k0 = 10_000 # system timescale factor if slow=False
    x = sinus.int(ic=+1, slow=False)
    y = sinus.int(ic=0, slow=False)
    
    sinus.connect(x, y)
    sinus.connect(y, x, weight=-1)
    
    sinus.measure(x)
    sinus.measure(y)
    channels = 2
    
    hc.set_circuit(sinus.generate())
    
    # this will just show roughly 1.5 wavelengths within the simulation
    t_final_ns = 900_000
    t_final_sec = t_final_ns / 1e9
    points_per_sec = 125_000 # something smallish for a quick result
    delta_t = 1./points_per_sec
    num_points = int(t_final_sec / delta_t)
    
    hc.set_daq(num_channels=2, sample_rate=points_per_sec)
    hc.set_run(op_time=t_final_ns)

    run = hc.start_run()
    data = np.array(run.data())
    
    assert data.shape == (num_points, channels)
    x_measured, y_measured = data.T
    
    t = np.linspace(0, t_final_sec, num_points)
    assert len(data) == len(t)

    # analytical solution to test problem:
    x_expected = -np.cos(t * k0) # corresponds to ic=+1
    y_expected = +np.sin(t * k0) # corresponds to ic=0
    
    assert np.allclose(x_expected, x_measured, atol=1e-2)
    assert np.allclose(y_expected, y_measured, atol=1e-2)


def test_ramp(endpoint):
    # Probably use @pytest.mark.parametrize instead to spawn "more tests"
    # and thus be faster
    hc = LUCIDAC(endpoint)
    hc.reset_circuit()

    slopes   = [-1,-0.5, 0, +0.5,+1]
    slopes  += [-10, -5, +5, +10]
    lanes    = [0,7,15,16,27,31] # no need to test range(0,32) in an emulator!
    
    slow = False

    res = []
    for lane in lanes:
        for slope in slopes:
            hc.reset_circuit()
            measure_ramp(hc, slope, lane, const_value=-1, slow=slow, do_assert=True)
        
