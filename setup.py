#!/usr/bin/env python3

import setuptools, subprocess

exec = lambda cmd: subprocess.check_output(cmd.split()).decode().strip()

def get_version():
    try:
        ver = exec("git describe --tags --long") # something like "v0.1.0-1234-g123456"
        vABC, commits, githash = ver.split("-")
        versionlist = vABC.split(".") # major includes the "v"
        major, minor = versionlist[0], versionlist[1]
        patch = commits
        version = f"{major}.{minor}.{patch}"
        return version
    except (subprocess.CalledProcessError, FileNotFoundError): # no git installed
        return "v0.1.1234"

setuptools.setup(
    name="lucipy",
    version=get_version(),
)
