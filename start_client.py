#!/usr/bin/env python3

import sys
from lucipy import *
simu = LUCIDAC("tcp://localhost:"+sys.argv[1])
print(simu.get_entities())
