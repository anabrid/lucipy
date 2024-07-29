from pydho800.pydho800 import PYDHO800, OscilloscopeRunMode
from lucipy import LUCIDAC, Circuit, Route, Connection
import matplotlib.pyplot as plt
from pprint import pprint

def test_coeff(ode, coeff):
  x = ode.int(id=0, ic=1)
  y = ode.int(id=1, ic=0)
  m = ode.mul()
  #c = ode.int(id=1, ic=+1) # constant giver
  c = 7
  
  routes = [
    Route(c,  0, -0.5,  m.a),
    Route(c,  1, -1.0,  m.b),
    #Route(x.out,  0,     +0.5,  y.a),
    #Route(y.out,  coeff, -0.5,  x.a),
    
    # view-only routes
    # keep in mind lane 8 is defective
    Route(c,  8,   0,  0),
    Route(m.out,  9,   0,  0),
  ]
  return routes

def lorentz(ode):
  x = ode.int(id=0, ic=-1)
  y = ode.int()
  z = ode.int()
  mxy = ode.mul() # -x*y
  xs = ode.mul(id=2)  # +x*s
  c = ode.const() #Const(0, 7)
 
  connections = [
    
    Connection(x.out,  x.a, weight=-1),
    Connection(y.out,  x.a, weight=-1.8), #exp2
    
    Connection(x.out, mxy.a),
    Connection(y.out, mxy.b),
    
    Connection(mxy.out, z.a, weight=-1.5),
    Connection(z.out,   z.a, weight=-0.2667),
    
    Connection(x.out, xs.a, weight=-1),
    Connection(z.out, xs.b, weight=+2.67), # experimentally - to +
    Connection(c,     xs.b, weight=-1), # exp
    
    Connection(xs.out, y.a, weight=-1.536), # exp
    Connection(y.out,  y.a, weight=-0.1),
    
    # dummy connections for ACL_OUT
    Route(x.out, 8, 0, 6),
    Route(y.out, 9, 0, 6)
    
  ]
  for x in connections: print(x)
  
  ode.add(connections)

# connect to osci
lucidac_ip = "192.168.150.127"
osci_ip = "192.168.150.136"

# connect to LUCIDAC and prep data
hc = LUCIDAC("tcp://" + lucidac_ip)

hc.slurp()
hc.query("reset")

coeff=1  

ode = Circuit()
#ode.add(test_coeff(ode, coeff))
lorentz(ode)
config = ode.generate()

pprint(config)

hc.set_config(config)
hc.set_op_time(ms=1000)
hc.run_config.halt_on_overload = False

hc.start_run()

if False:
  with PYDHO800(address = osci_ip) as dho:
    print(f"Identify: {dho.identify()}")

    dho.set_channel_enable(0, True)
    dho.set_channel_enable(1, True)
    dho.set_channel_enable(2, False)
    dho.set_channel_enable(3, False)

    dho.set_channel_scale(0, 5.0)
    dho.set_channel_scale(1, 5.0)
    dho.set_timebase_scale(1e-2)

    tx_depth = dho.memory_depth_t.M_10M
    dho.set_memory_depth(tx_depth)

    dho.set_run_mode(OscilloscopeRunMode.RUN)
    hc.start_run()
    dho.set_run_mode(OscilloscopeRunMode.STOP)

    data = dho.query_waveform((0, 1))
    print(data)
    
    # plot data
    x = data["y0"]
    y = data["y1"]
    
    #plt.ion()

    fig, ax = plt.subplots()
    ax.plot(x, label="x")
    ax.plot(y, label="y")
    #ax.scatter(x, y, s=0.1)
    #ax.set_xlabel("X")
    #ax.set_ylabel("Y")
    ax.grid(True, linestyle='--', color='lightgray')
    plt.legend()
    plt.show()
    
  #  hc.sock.sock.close()

