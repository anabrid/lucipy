#!/usr/bin/env python3

from lucipy import LUCIDAC, Circuit, Route, Connection, Simulation
from time import sleep 

### Idee:
###
### Sinus auf einem REV1 System mit fehlenden ICs erzeugen
### durch lange laufen lassen.

# M0 = M-Block INT
# M1 = M-Block MUL

### attention, do not use rev1.int() and friends as this is still
###     in REV0 numeration (where M1 and M0 are swapped)

i0, i1 = 2,4

hc = LUCIDAC()
print(hc)

def sinus(i0, i1):
    "This tests the INTEGRATORS"
    rev1 = Circuit()
    
    #rev1.set_ic(i0, +1)
    #rev1.set_ic(i1, 0)
    
    rev1.int(id=i0, ic=+1, slow=False)
    rev1.int(id=i1, ic=0, slow=False)
    
    rev1.route(i0, 2,  0.25, i1)
    rev1.route(i1, 3, -0.5,  i0)
    rev1.probe(i0, front_port=6)
    rev1.probe(i1, front_port=7)

    print(rev1)

    # the following works ONLY on a REV1

    hc.reset_circuit()

    # filter out M1 because there is nothing to set
    # and MCU complains if I try to configure something nonexisting
    config = { k:v for k,v in rev1.generate().items() if not "/M1" in k }

    hc.set_config(config)

    # set all ACL channels to external
    hc.query("set_circuit", {"entity": [hc.get_mac() ], "config": {
        "acl_select": [ "external" ]*8,
        "adc_channels": [ i0, i1 ],    
    }})


    manual_control = True

    if manual_control:
        hc.manual_mode("ic")
        sleep(0.5)
        hc.manual_mode("op")
        sleep(0.5)
    else:
        hc.set_daq(num_channels=2, sample_rate=125_000)
        nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
        hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

        run = hc.start_run()
        

def lane_sinus(lane0, lane1):
    "This tests the INTEGRATORS"
    rev1 = Circuit()
    
    #rev1.set_ic(i0, +1)
    #rev1.set_ic(i1, 0)
    
    rev1.int(id=i0, ic=+1, slow=False)
    rev1.int(id=i1, ic=0, slow=False)
    
    rev1.route(i0, lane0,  1, i1)
    rev1.route(i1, lane1, -1,  i0)
 
    rev1.probe(i0, front_port=6)
    rev1.probe(i1, front_port=7)

    print(rev1)

    # the following works ONLY on a REV1

    hc.reset_circuit()

    # filter out M1 because there is nothing to set
    # and MCU complains if I try to configure something nonexisting
    config = { k:v for k,v in rev1.generate().items() if not "/M1" in k }

    hc.set_config(config)

    manual_control = True

    if manual_control:
        hc.manual_mode("ic")
        sleep(0.5)
        hc.manual_mode("op")
        sleep(0.5)
    else:
        hc.set_daq(num_channels=2, sample_rate=125_000)
        nonexisting_ic = 10 # ns, just not to confuse FlexIO. Current Integrators don't support IC ;-)
        hc.set_run(halt_on_overload=False, ic_time=200_000, op_time=1_000_000)

        run = hc.start_run()

lane_sinus(2,4)
