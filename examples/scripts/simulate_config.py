#!/usr/bin/env python3

# Small demo script for reading in a LUCIDAC JSON configuration
# file and simulating it.
#
# An example (Lorenz attractor) is given, you can invoke it with:
#
#  python simulate_config.py --plot simulate_config_example.txt
#
# Hint, run "export PYTHONPATH=../.." if you want to use lucipy without
# installation.

from lucipy import Circuit, Simulation

import argparse, sys, json

parser = argparse.ArgumentParser()

parser.add_argument('config', nargs='?', type=argparse.FileType('r'), help="JSON configuration file. If none is given, will read from stdin")

parser.add_argument('--optime_us', default=0, help="Optime in microseconds (all given optimes are added)")
parser.add_argument('--optime_ms', default=0, help="Optime in milliseconds (all given optimes are added)")
parser.add_argument('--optime_sec', default=0, help="Optime in seconds (all given optimes are added)")

parser.add_argument('--show-routes', help="Show routes")
parser.add_argument('--plot', action="store_true", help="Do a plot. Otherwise will dump simulation results")

args = parser.parse_args()

if not args.config:
    print("Expecting JSON configuration on STDIN...", file=sys.stderr)
    args.config = sys.stdin
    fname = "-stdin-"
else:
    fname = args.config.name

config = json.load(args.config)

circuit = Circuit()
circuit.load(config)

if args.show_routes:
    print(circuit)

sim = Simulation(circuit, realtime=True)

optime_sec = args.optime_us/1e6 + args.optime_ms/1e3 + args.optime_sec

if optime_sec == 0:
    print("No optime given, will use 100ms.", file=sys.stderr)
    optime_sec = 0.1

res = sim.solve_ivp(optime_sec)

import numpy as np
used_integrator = np.all(res.y != 0, axis=1)

if args.plot:
    import matplotlib.pyplot as plt
    for i,used in enumerate(used_integrator):
        if used:
            plt.plot(res.t, res.y[i,:], label=f"Integrator {i}")
    plt.xlabel("Simulation time [sec]")
    plt.ylabel("Analog units")
    plt.title(f"Time evolution of {fname}")
    plt.tight_layout()
    plt.show()
else:
    print("time", *[ f"int{i}" for i,used in enumerate(used_integrator) if used ])
    for i,t in enumerate(res.t):
        print(t, * res.y[used_integrator,i].tolist())
