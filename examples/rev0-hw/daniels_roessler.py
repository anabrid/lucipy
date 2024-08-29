from pydho800.pydho800 import PYDHO800, OscilloscopeRunMode
from lucipy import LUCIDAC, Circuit, Route
import matplotlib.pyplot as plt

def roessler(ode):
  x = ode.int(id=0, ic=-0.0666)
  y = ode.int(id=1, ic=0)
  z = ode.int(id=2, ic=0)
  
  routes = [
    Route(8,   0,   1.25, 9),
    Route(9,   1,  -0.8,  8),
    Route(10,  2, -2.3,   8),
    Route(9,   3,  0.4,   9),
    Route(4,   4, -0.005,10),
    Route(8,   5,  1.0,   0),
    Route(4,  14,  0.38,  0),
    Route(10, 15, 15.0,   1),
    Route(0,  16, -1.0,  10),
    Route(8,  8,   0.0,  9),
    Route(9,  9,   0.0,  9)
  ]
  return routes

def main():
  # connect to osci
  lucidac_ip = "192.168.150.127"
  osci_ip = "192.168.150.136"

  # connect to LUCIDAC and prep data
  hc = LUCIDAC("tcp://" + lucidac_ip)

  ode = Circuit()
  ode.add(roessler(ode))
  config = ode.generate()

  hc.set_config(config)
  hc.set_op_time(ms=1000)
  
  with PYDHO800(address = osci_ip) as dho:
    print(f"Identify: {dho.identify()}")

    dho.set_channel_enable(0, True)
    dho.set_channel_enable(1, True)
    dho.set_channel_enable(2, False)
    dho.set_channel_enable(3, False)

    dho.set_channel_scale(0, 5.0)
    dho.set_channel_scale(1, 5.0)
    dho.set_timebase_scale(1e-4)

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

    fig, ax = plt.subplots()
    # ax.scatter(x, y, s=0.1)
    ax.plot(y)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle='--', color='lightgray')
    plt.show()

if __name__ == "__main__":
  main() 
