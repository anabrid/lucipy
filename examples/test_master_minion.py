#!/usr/bin/env python3

from lucipy import *

master = LUCIDAC("tcp://192.168.68.116") # floating teensy
minion = LUCIDAC("tcp://192.168.68.109") # actual lucidac/REV1 hardware

group = master.master_for(minion)

# this just works
group.manual_mode("op")
group.manual_mode("ic")

# daq does not yet work due to firmware limitation.
# however, manual_mode does not support DAQ anyway.

# group.start_run does not work with my floating teensy
# due to hardware limitation.
