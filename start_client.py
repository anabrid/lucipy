#!/usr/bin/env python3

import sys
from lucipy import *
simu = LUCIDAC("tcp://127.0.0.1:"+sys.argv[1])
print(simu.get_entities())
