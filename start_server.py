#!/usr/bin/env python

import sys, subprocess
from lucipy import Emulation

emu = Emulation(bind_addr="0.0.0.0", bind_port=int(sys.argv[1]))

# use this in particular with python debugger
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
