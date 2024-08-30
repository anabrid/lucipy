from lucipy import LUCIDAC

from pylab import *
from itertools import product

import sys
sys.path.append("../../test")
from test_hardware import measure_ramp

emu = False
if emu:
    hc = LUCIDAC("emu:/?debug")
else:
    hc = LUCIDAC()
    
#hc.sock.sock.debug_print = True


#slopes = [+1, -1]
#slopes   = linspace(-1, 1, num=20).tolist()
slopes  = [-1,-0.5, 0, +0.5,+1]
slopes  += [-10, -5, +5, +10]
lanes   = range(0,32) #range(26,32)

#ion()

"""
import sys, traceback

class TracePrints(object):
  def __init__(self):    
    self.stdout = sys.stdout
  def write(self, s):
    self.stdout.write("Writing %r\n" % s)
    traceback.print_stack(file=self.stdout)

sys.stdout = TracePrints()
"""

res = []
for lane in lanes:
    clf()
    for slope in slopes:
        hc.reset_circuit()
        valid_endpoint, valid_evolution, x = measure_ramp(hc, slope, lane, const_value=-1, slow=True)
        
        label = f"{slope=}" if not valid_endpoint or not valid_evolution else None
        title(f"{lane=} Ramp test")
        plot(x, "o-", label=label)

        ires = (slope, lane, valid_endpoint, valid_evolution)
        res.append([*ires, x])
        print(*ires)
    legend() # will warn if no errors occured ;)
    savefig(f"ramp-test-{'emu' if emu else ''}{lane=}.png")

#legend().set_draggable(True)
