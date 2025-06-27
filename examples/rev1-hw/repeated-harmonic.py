##
# Simple harmonic oscillators, repeated for a number of times. This example uses
# the run configurations `repetitive` parameter 
## 

import json
from lucipy import Circuit, LUCIDAC
import matplotlib.pyplot as plt
import numpy as np

# initial value for the SIN component
sin_ic = -0.42
# sin_ic = 0

# number of cycles that should be executed
num_cycles = 5

# create circuit - simple harmonic oscilllators
m = Circuit()

isin = m.int(ic = sin_ic, slow = True)
icos = m.int(slow = True)

m.connect(isin, icos, weight = 1.0)
m.connect(icos, isin, weight = -1.0)

m.measure(isin, adc_channel=0)
m.measure(icos, adc_channel=1)

config = m.generate()

# send to LUCIDAC and retrieve results
op_secs = 0.1 # duration of a single OP cycle

luci = LUCIDAC()
luci.set_circuit(m)
luci.set_daq(sample_rate=1_000)
luci.set_run(
  ic_time = 1000, 
  op_time=int(op_secs * 1_000_000_000),
  halt_on_overload=False,
  repetitive=True)
run = luci.run()

# receive data and concatenate over all cycles
data = []
cycles = 0
for ix, new_data in enumerate(run.next_data(mark_op_end_by_none=True)):
  if new_data is not None:
    data += new_data
  else:
    # if data is NONE, an OP cycle has been successfully ended
    print("<IP/OP CYCLE ENDED>")
    cycles += 1

    if cycles == num_cycles:
      break

# stop the run - from here on out, ignore all incoming messages
has_stopped = run.stop()

# use matplotlib to plot the resulting curves
x = np.linspace(0, num_cycles * op_secs, len(data))
plt.plot(x, [t[0] for t in data], x, [t[1] for t in data])
plt.show()