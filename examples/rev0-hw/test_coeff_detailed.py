from pydho800.pydho800 import PYDHO800, OscilloscopeRunMode
from lucipy import LUCIDAC, Circuit, Route
import matplotlib.pyplot as plt
from time import sleep
import numpy as np

def test_coeff(lane, coeff):
  i = 1 # zweiter Integrierer
  x = 8+i # int0
  c = 7 # const from mul

  circuit = Circuit([
    Route(c, lane, coeff,  x),
    
    # view-only routes
    # keep in mind lane 8 is defective
    Route(x,  8,   0,  7),
  ])
  
  # set INT0 to SLOW
  circuit.set_k0(el=i, val=100)
  
  return circuit

# connect to osci
lucidac_ip = "192.168.150.127"
osci_ip = "192.168.150.136"

# connect to LUCIDAC and prep data
hc = LUCIDAC("tcp://" + lucidac_ip)
hc.slurp()
hc.query("reset")

steer_dho = False
if steer_dho:
  dho = PYDHO800(address = osci_ip)
  dho.connect()
  print(f"Identify: {dho.identify()}")

  dho.set_channel_enable(0, True)
  dho.set_channel_enable(1, True)
  dho.set_channel_enable(2, False)
  dho.set_channel_enable(3, False)

  dho.set_channel_scale(0, 5.0)
  dho.set_channel_scale(1, 5.0)
  #dho.set_timebase_scale(0.001) # roll mode

  tx_depth = dho.memory_depth_t.M_10M
  dho.set_memory_depth(tx_depth)

def run(lane, coeff, optime_us):
  print(f"{lane=}, {coeff=}, {optime_us=}")
  config = test_coeff(lane, coeff).generate()
  hc.set_config(config)
  hc.set_op_time(ms=1000)

  manual_mode = True
  if manual_mode:
    hc.query("manual_mode", dict(to="ic"))
    if steer_dho:
      dho.set_run_mode(OscilloscopeRunMode.RUN)
    sleep(1)
    hc.query("manual_mode", dict(to="op"))
    sleep(3)
    if steer_dho:
      dho.set_run_mode(OscilloscopeRunMode.STOP)
    hc.query("manual_mode", dict(to="halt"))
  else:
    hc.set_op_time(us=optime_us) # for coeff = +5
    #hc.set_daq(num_channels=1)
    hc.run_config.halt_on_overload = False

    if steer_dho:
      dho.set_run_mode(OscilloscopeRunMode.RUN)
    hc.slurp()
    try:
      run = hc.start_run()
    except:
      pass
    hc.slurp()
    if steer_dho:
      dho.set_run_mode(OscilloscopeRunMode.STOP)

  if steer_dho:
    data = dho.query_waveform((0, 1))
    
    print("%2d % 3.4f % 1.3f % 1.3f % 1.3f" % (lane, coeff,
        np.min(data["y0"]),
        np.max(data["y0"]),
        np.average(data["y0"]),
    ))
  """
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
  plt.title(f"{lane=}, {coeff=}")
  plt.legend()
  plt.show()
  """

if False:
      # kleine Wert
      optime_us = 200
      for coeff in [-0.5, +0.5]:
        for lane in range(32):
            if lane == 8:
                continue
            run(lane, coeff, optime_us)
            input("next run>")
      
      input("Change oscilloscope to us=100")
      # große Werte
      optime_us = 20
      for coeff in [-10, +10]:
        for lane in range(32):
            if lane == 8:
                continue
            run(lane, coeff, optime_us)
            input("next run>")
else:
  run(0, +0.5, 20*100)
