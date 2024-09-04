from lucipy import Circuit, Route, Connection, Simulation
from time import sleep
import numpy as np
import random

sign = lambda val: abs(val) / val

# This file contains *simple* circuits which can be well tested automatically

def measure_ics(hc, ic, slow=True, do_assert=False):
    c = Circuit()
    for i in range(8):
        I = c.int(id=i, ic=ic, slow=slow)
        c.measure(I)
    # so we don't want to create a lot of dummy routes, therefore we leave out
    # the empty U-C-I and configure things manually...
    config = c.generate()
    for k in ["/U", "/C", "/I"]:
        del config["/0"][k]

    hc.set_circuit(config)
    # hc.manual_mode("ic") # is expected
    # 90ms is required for slow k0 is this waiting time is sufficient, +network delay
    sleep(0.1)
    measured = hc.one_shot_daq()["data"]
    
    int_sign = -1 # keep in mind the negating integrators
    compare_measured = int_sign * np.array(measured)
    
    valid = np.allclose(ic, compare_measured, rtol=0.2, atol=0.2)
    
    print(f"{ic=}, {slow=}, {valid=}, {compare_measured=}")
    
    if do_assert:
        assert valid
    
    return compare_measured, valid

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

def circuit_sinus(i0=0, i1=1, l0=2, l1=3):
    s = Circuit()
    
    x = s.int(id=i0, ic=+1)
    y = s.int(id=i1, ic=0)
    
    s.add( Route(x, l0,  1, y) )
    s.add( Route(y, l1, -1, x) )
    
    s.measure(x)
    s.measure(y)
    
    return s

def mostclose(a,b, atol, more_then):
    # Variant of np.allclose which accepts glitches
    return sum(abs(a-b) < atol) / a.size > more_then
    # TODO: Just use sum(isclose()) > more_then

def measure_sinus(hc, i0, i1, l0, l1):
    #hc.reset_circuit()
    
    hc.set_circuit(circuit_sinus(i0,i1,l0,l1).generate(skip="/M1"))
    
    k0 = 10_000 # system timescale factor if slow=False
    
    
    # this will just show roughly 1.5 wavelengths within the simulation
    hc.set_daq(num_channels=2, sample_rate=125_000)
    hc.set_run(halt_on_overload=False, ic_time=200_000)
    hc.set_op_time(us=900)
    
    # activate Non-FlexIO code
    hc.run_config.no_streaming = True
    
    data = np.array(hc.start_run().data())
    x_measured, y_measured = data[:,0], data[:,1]
    
    # TODO Testing with only one channel
    #x_measuredm, y_measured = data[0], 0
    
    t = np.linspace(0, hc.run_config.op_time/1e9, len(data))

    # analytical solution to test problem:
    x_expected = -np.cos(t * k0) # corresponds to ic=+1
    y_expected = +np.sin(t * k0) # corresponds to ic=0
    
    valid =     mostclose(x_expected, x_measured, atol=0.4, more_then=0.9) \
            and mostclose(y_expected, y_measured, atol=0.4, more_then=0.9)
    
    return valid, x_measured, y_measured, x_expected, y_expected


def measure_ramp(hc, slope=1, lane=0, const_value=+1, slow=False, do_assert=False, fake_upscale=False):
    # This circuit uses the constant giver for integrating over a constant
    
    upscaling = abs(slope) > 1
    downscaling = 10 if upscaling else 1
    slow_time = 100 if slow else 1
    
    ic = -slope*const_value/downscaling
    
    # 0 -> clane 14, 1 -> clane 15
    constant_giver = 1 if lane < 16 else 0
    
    t_final = 2 / downscaling * slow_time
    expected_result = -(t_final*const_value*slope/slow_time + ic)
    print(f"{slope=} -> {ic=}, {t_final=}, {expected_result=}")
    assert expected_result == ic
    print(f"{ic=}, {t_final=}, {expected_result=}")

    ramp = Circuit()
    i = ramp.int()
    assert i.out == 0
    
    c = ramp.const(constant_giver)
    assert c.out == 14+constant_giver
    
    if const_value != +1:
        # overwrite the constant to use
        ramp.use_constant(const_value)
    
    #ramp.connect(c, i, weight=slope)
    
    # do not use c.out, this way cross-checking if the const
    # is available at that lane
    ramp.route(c, lane, slope, i.a)
    
    ramp.set_ic(0, ic)
    ramp.set_k0_slow(0, slow)
    
    channel = ramp.measure(i)
    
    conf = ramp.generate(skip="/M1")
    
    if fake_upscale:
        for ii in range(32):
            conf["/0"]["/I"]["upscaling"][ii] = True
    
    hc.set_circuit(conf)
    ic_time_ns = 90_000_000 if slow else 200_000
    op_time_ns = 200_000 * slow_time/downscaling
    hc.set_run(halt_on_overload=False, ic_time=ic_time_ns, op_time=op_time_ns, no_streaming=True)

    run = hc.start_run()
    data = np.array(run.data())
    x_hw = data.T[channel]
    t_hw = np.linspace(0, t_final, len(x_hw))
    
    if len(x_hw) <= 1:
        print(f"Warning!! Did not get any real data from LUCIDAC: {x_hw=}")
    
    # Attention: The simulation will interpolate on the measurements of the real computer.
    #            If no real aquisition took place, the difference will not be useful.
    
    sim = Simulation(ramp)
    assert sim.constant[0] == slope*const_value
    assert all(sim.constant[1:] == 0)
    sim_data = sim.solve_ivp(t_final, dense_output=True)
    t_sim = t_hw
    x_sim = sim_data.sol(t_hw)[i.id]
    # instead of:
    # x_sim = sim_data.y[i.id]
    # t_sim = sim_data.t

    # Large tolerance mainly because of shitty non-streaming
    # data aquisition
    if len(x_hw) > 1:
        assert np.isclose(x_sim[-1], expected_result, atol=0.01)
    valid_endpoint = np.isclose(x_hw[-1],  expected_result, atol=0.3)
    valid_evolution = np.allclose(x_sim, x_hw, atol=0.2)
    
    if do_assert:
        # Having assert in this frame to get access to local variables with pdb
        assert valid_endpoint and valid_evolution
    
    return valid_endpoint, valid_evolution, x_hw

def measure_exp(hc, alpha=-1, ic=+1, lane=0):
    if sign(alpha) > 0:
        y_final = 1 # integrate until overload
    else:
        y_final = sign(ic) * 0.1 # integrate until a decent small value

    t_final = np.log(y_final/ic) / alpha
    assert t_final > 0

    e = Circuit()
    i = e.int(ic=ic)
    e.route(i, lane, -alpha, i)
    e.measure(i)
    hc.set_circuit( e.generate(skip="/M1") )
    hc.set_daq(num_channels=1)
    hc.set_run(halt_on_overload=False, ic_time=200_000, no_streaming=True)
    hc.set_op_time(us=200)#k0fast=t_final)
    
    data = np.array(hc.start_run().data())
    x_hw = data[:,0]
    t_hw = np.linspace(0, t_final, len(x_hw))
    
    res = Simulation(e).solve_ivp(t_final, realtime=True, dense_output=True)
    t_sim = t_hw
    x_sim = res.sol(t_hw)[i.id]
    
    #return x_hw,x_sim,t_sim
    
    valid_evolution = np.allclose(x_sim, x_hw, atol=0.1)
    return valid_evolution, x_hw, x_sim

def measure_cblock_stride(hc, lanes, test_values):
    "Expect (currently) 2 lanes and 2 mdac test values"
    k = Circuit()
    assert len(lanes) == len(test_values)
    assert len(lanes) < 4 # limited by math id elements

    use_constant_giver = False
    if use_constant_giver: # constants from Ublock
        c0, c1 = k.const(0), k.const(1)
    else: # constant from IC values from an integrator
        # ic=-1: negate the constant because int output is negated
        c0 = k.int(ic=-1)# -0.1)
        c1 = c0
        # You have to manually ensure that you called
        # hc.manual_mode("ic") before using this branch!
    mids = k.identities(len(lanes)) # Math Identity elements
    # just to make a few more needless routes
    sink = k.int(id=7) # something non-used
    
    for lane in range(32):
        c = c1 if lane < 16 else c0
        if lane in lanes:
            i = lanes.index(lane)
            test_value = test_values[i]
            k.route(c, lane, test_value, mids[i])
        else:
            # the following is not useful because we cannot access
            # these values, but just toggle more switches, we configure
            # it anyway.
            k.route(c, lane, 0.123, sink)
    
    channels = np.array([k.measure(mid) for mid in mids])
    #print(k)
    
    #hc.reset_circuit()
    #print(k.generate())
    
    print(".",end='',flush=True) # some progress indicator
    
    # No sanity check: surpress identity-not-used-as-mul's warnings
    conf = k.generate(skip="/M1", sanity_check=False)
    
    if not use_constant_giver:
        assert not k.u_constant
        assert not "constant" in conf["/0"]["/U"] or not conf["/0"]["/U"]["constant"]
    
    hc.set_circuit(conf)
    return np.array(hc.one_shot_daq()["data"])[channels]


def measure_cblock_stride_variable(hc, lanes, uin_values, coeff_values):
    
    # Status of this function: Untested, should probably be deleted.
    
    
    """
    CBlock characterization by variable input, i.e. not
    constant giver and not IC=+1 but really something where IC in [-1,+1]
    (upscaling made via I-block).
    
    Expects len 2 vectorial inputs per argument
    """
    k = Circuit()
    
    # You have to manually ensure that you called
    # hc.manual_mode("ic") before using this function!

    assert len(lanes) == len(uin_values)
    assert len(coeff_values) == len(uin_values)
    assert len(lanes) < 4 # limited by math id elements
    
    ic_upscaling = 10 if abs(val) > 1 else 1
    
    # constant from IC values from an integrator
    # ic=-coeff_values: negate the constant because int output is negated
    consts = [ k.int(ic=-val/ic_upscaling) for val in uin_values ]
        
    mids = k.identities(len(lanes)) # Math Identity elements
    
    # just to make a few more needless routes
    sink = k.int(id=7) # something non-used
    
    for lane in range(32):
        if lane in lanes:
            i = lanes.index(lane)
            k.route(consts[i], lane, coeff_values[i] * ic_upscaling, mids[i])
        else:
            # the following is not useful because we cannot access
            # these values, but just toggle more switches, we configure
            # it anyway.
            k.route(consts[0], lane, 0.123, sink)
    
    channels = np.array([k.measure(mid) for mid in mids])
    proofs   = np.array([k.measure(ic_const_giver) for ic_const_giver in consts])
    #print(k)
    
    #hc.reset_circuit()
    #print(k.generate())
    
    print(".",end='',flush=True) # some progress indicator
    
    # No sanity check: surpress identity-not-used-as-mul's warnings
    conf = k.generate(skip="/M1", sanity_check=False)
    
    assert not k.u_constant
    assert not "constant" in conf["/0"]["/U"] or not conf["/0"]["/U"]["constant"]
    
    hc.set_circuit(conf)
    sampled_data = np.array(hc.one_shot_daq()["data"])
    input_data = sampled_data[proofs]
    output_data = sampled_data[channels]
    # interestingly, input_data is just garbarage. Need to check...
    #assert np.allclose(input_data.tolist(), coeff_values, rtol=0.2)
    return output_data

def measure_cblock(hc, test_values):
    "Expects 32 test_values"
    from lucipy.circuits import window
    
    stride_size = 2 # use only 2 MathID-elements because other seem broken
    shape = (int(32/stride_size), stride_size)
    all_stride_lanes = np.arange(32).reshape(*shape).tolist()
    all_test_values = np.array(test_values).reshape(*shape).tolist()
    stride_results = [ measure_cblock_stride(hc,*stride) \
        for stride in zip(all_stride_lanes, all_test_values)]

    return np.array(stride_results).flatten()

def measure_cblock_variable(hc, uin_values, coeff_values):
    "Expects 32 uin_values, 32 coeff_values"
    from lucipy.circuits import window
    
    stride_size = 2 # use only 2 MathID-elements because other seem broken
    shape = (int(32/stride_size), stride_size)
    all_stride_lanes = np.arange(32).reshape(*shape).tolist()
    all_uin_values = np.array(uin_values).reshape(*shape).tolist()
    all_coeff_values = np.array(coeff_values).reshape(*shape).tolist()
    stride_results = [ measure_cblock_stride(hc,*stride) \
        for stride in zip(all_stride_lanes, all_test_values, all_coeff_values)]

    return np.array(stride_results).flatten()
