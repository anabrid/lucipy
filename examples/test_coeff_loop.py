from pydho800.pydho800 import PYDHO800, OscilloscopeRunMode
from lucipy import LUCIDAC, Circuit, Route
import matplotlib.pyplot as plt
from time import sleep

def test_coeff(ode, coeff):
  x = ode.int(id=0, ic=1)
  y = ode.int(id=1, ic=0)
  #c = ode.int(id=1, ic=+1) # constant giver
  const_from_mul = 7
  
  routes = [
    Route(const_from_mul,  coeff, -0.5,  x.a),
    #Route(x.out,  0,     +0.5,  y.a),
    #Route(y.out,  coeff, -0.5,  x.a),
    
    # view-only routes
    # keep in mind lane 8 is defective
    Route(x.out,  8,   0,  0),
    Route(y.out,  9,   0,  0),
  ]
  return routes

# connect to osci
#lucidac_ip = "192.168.150.127"
lucidac_ip = "192.168.100.143"
# osci_ip = "192.168.150.136"

# connect to LUCIDAC and prep data
hc = LUCIDAC("tcp://" + lucidac_ip)


def rep():
  hc.query("manual_mode", dict(to="ic"))
#  dho.set_run_mode(OscilloscopeRunMode.RUN)
  sleep(0.3)
  hc.query("manual_mode", dict(to="op"))
  sleep(0.3)
  hc.query("manual_mode", dict(to="halt"))

for coeff in range(1,32):
  print(f"TESTING {coeff=}")
  hc.slurp()
  hc.query("reset")
  
  if coeff == 8 or coeff == 9:
    continue

  ode = Circuit()
  ode.routes = [] # PROGRAMMING ERROR
  ode.add(test_coeff(ode, coeff))
  config = ode.generate()

  hc.set_config(config)
  hc.set_op_time(ms=1000)

  """
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
  """

  hc.query("manual_mode", dict(to="ic"))
#  dho.set_run_mode(OscilloscopeRunMode.RUN)
  sleep(0.3)
  hc.query("manual_mode", dict(to="op"))
  sleep(0.3)
  hc.query("manual_mode", dict(to="halt"))
  
  """
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
      plt.title(f"Lane = {coeff}")
      plt.legend()
      plt.show()
  """
    
#  hc.sock.sock.close()

