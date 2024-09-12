#!/usr/bin/env python

# Small script for sending a single command straight from the command line.
# Will return the output as JSON.
# Example:
#
#  python send_command.py sys_reboot
#
# Expects the LUCIDAC_ENDPOINT environment variable to be set
#
# Hint, run "export PYTHONPATH=../.." if you want to use lucipy without
# installation.

from lucipy import LUCIDAC

import argparse, sys, json

parser = argparse.ArgumentParser()

#parser.add_argument('config', nargs='?', type=argparse.FileType('r'), help="JSON configuration file. If none is given, will read from stdin")

parser.add_argument('command', help="Actual command to run")

args = parser.parse_args()

#if not args.config:
#    print("Expecting JSON configuration on STDIN...", file=sys.stderr)
#    args.config = sys.stdin
#    fname = "-stdin-"
#else:
#    fname = args.config.name

hc = LUCIDAC()

if hasattr(hc, args.command):
    method = getattr(hc, args.command)
    res = method()
    res_json = json.dumps(res, indent=4) # TODO: Make command line argument whether to format
    print(res_json)
else:
    print(f"Command hc.{args.command}() not known.")
