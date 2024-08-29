#!/usr/bin/env python3

from lucipy import LUCIDAC

### Steering the Front panel for LUCIDAC

hc = LUCIDAC()

# this works:
hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {  "/FP":  {"leds": 0xaa } } })

# this works too:
hc.query("set_circuit", {"entity": [hc.get_mac(), "FP" ], "config": { "leds": 0x55  } })

# now we can do cool stuff such as:

while True:
    hc.set_leds(0x55)
    hc.set_leds(0xaa)
    
# which clearly shows how long such queries take!
