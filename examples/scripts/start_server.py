#!/usr/bin/env python
#
# Example script showing how to invocate the emulated LUCIDAC server.
#
# Usage:
#
#  export PYTHONPATH=../..  # uses lucipy without installing
#  python start_server.py
#
#

import sys, subprocess
from lucipy import Emulation

# either use port given or let OS choose the port
port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
emu = Emulation(bind_addr="0.0.0.0", bind_port=port)

# use this version in particular with python debugger
emu.serve_blocking()

threading = False
if threading:
    thread = next(emu.serve_threading())
    print(f"Waiting for server {emu.endpoint()} thread to finish, can also do other work")
    thread.join()

multiprocessing = False    
if multiprocessing:
    proc = emu.serve_forking()
    print(f"Waiting for server {emu.endpoint()} process to finish, can also do other work") 
    proc.join()
