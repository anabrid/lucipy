#!/usr/bin/env python3

import sys, uuid
from pprint import pprint
sys.path.append("..") # use that lucipy in parent directory

from lucipy import LUCIDAC, Circuit, Route

hc = LUCIDAC("tcp://192.168.150.127")
ode = Circuit()

def roessler():
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

# funktionsfaehig:
sinus_von_pybrid = \
    {'entity': None,
 'config': {'/0': {'/M0': {'elements': [{'ic': 0.709971666, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000},
     {'ic': 0, 'k': 10000}]},
   '/M1': {},
   '/U': {'outputs': [8,
     9,
     None,
     None,
     None,
     None,
     None,
     None,
     8,
     9,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     None]},
   '/C': {'elements': [1.00024426,
     -1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426,
     1.00024426]},
   '/I': {'outputs': [None,
     None,
     None,
     None,
     None,
     None,
     None,
     None,
     [1],
     [0],
     None,
     None,
     None,
     None,
     None,
     None]}}}}



def sinus():
    print("Sinus")
    hc.query("reset")
    #for i in range(8):
    #    ode.set_ic(el=i, val= (i+1) / 10)
    
    ode.set_ic(0, 0.7)
    
    routes_klappt = [
        Route(8, 0,  1.0, 9),
        Route(9, 1, -1.0, 8),
       # Route(8, 8,  0.0, 14),
        Route(9, 9,  0.0, 15),
    ]
        
    routes_falsch = [
        Route(8, 8,  1.0, 9),
        Route(9, 9, -1.0, 8)
    ]
    
    routes_klappt_vielleicht = [
        Route(8, 0,  1.0, 9),
        Route(9, 1, -1.0, 8),
        Route(8, 8,  1.0, 9),
        Route(9, 9, -1.0, 8),
    ]
    
    return routes_klappt_vielleicht

def constant():
    hc.query("reset")
    for i in range(8):
        ode.set_ic(el=i, val= (i+1) / 10)
    return [ Route(12, lane, 0.0, 4) for lane in range(32) ]

ode.add(roessler())

pprint(ode.generate())

config = ode.generate()
config["entity"] = "04-E9-E5-16-09-92"

#config = sinus_von_pybrid
sinus_von_pybrid["entity"] = config["entity"]

"""
outer_config = {
    "entity": ["04-E9-E5-16-09-92", "0"],
    "config": sinus_von_pybrid # config
}
hc.query("set_config", outer_config)
"""

# TODO: Move in Lib
for entity, entity_config in config["config"]["/0"].items():
    outer_entity_config = {
        "entity": ["04-E9-E5-16-09-92", "0"],
        "config": {
                entity: entity_config
            }
        }
    hc.query("set_config", outer_entity_config)


# TODO: Move in Lib
run_config = dict(
    halt_on_external_trigger = False,
    halt_on_overload  = True,
    ic_time = 50000, # 100_000, # ns
    op_time = 900_000_000, # 200_000_000, # ns
)

daq_config = dict(
    num_channels = 0,
    sample_op = True,
    sample_op_end = True,
    sample_rate = 500_000,
)

start_run = {
    "id": str(uuid.uuid4()),
    "session": None,
    "config": run_config,
    "daq_config": daq_config,
}

print("Start run")
hc.query("start_run", start_run)
