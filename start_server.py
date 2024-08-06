#!/usr/bin/env python

import sys
from lucipy import Emulation
Emulation(bind_addr="0.0.0.0", bind_port=int(sys.argv[1])).serve_forever()
