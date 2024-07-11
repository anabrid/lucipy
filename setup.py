#!/usr/bin/env python3

import setuptools, subprocess

exec = lambda cmd: subprocess.check_output(cmd.split()).decode().strip()

def get_version():
    try:
        ver = exec("git describe --tags") # something like "v0.1.0"
        #build = exec("git rev-parse --short HEAD") # something like "1f61552"
        #return f"{ver}+g{build}"
        return ver
    except (subprocess.CalledProcessError, FileNotFoundError): # no git installed
        return "v0.0.0+N/A-without-git"

setuptools.setup(
    name="lucipy",
    version=get_version(),
)
