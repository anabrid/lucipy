#!/usr/bin/env python3

# This is just a dummy client in order to test the standalone emulated server

import sys
from lucipy import *
simu = LUCIDAC("tcp://127.0.0.1:"+sys.argv[1])
print(simu.get_entities())
