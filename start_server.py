#!/usr/bin/env python

import sys
from lucipy import Emulation
Emulation(bind_port=int(sys.argv[1])).serve_forever()
