"""
The simple, stupid LUCIDAC python client classes.

Provides:

* LUCIDAC analog configuration and run managament
* An easy HybridController class
* Basic typing

Does not provide:

* Typing. Not yet sure.
* Administrative interface
* Async IO for exploiting all of parallelity single
  threaded python can provide.

Paradigms and software technical goodies:

* This is a small code with minimal dependencies
* Avoid boilerplate code by all means. Have sane defaults
  allowing to start with the LUCIDAC device quickly. This
  might not work for REDAC but does for LUCIDAC.
* No poetry, no deeply nested directories, no large class
  hierarchies, no large stack traces
* No async code
* Human friendly for getting started in programming,
  in particular in interactive settings like IPython and
  Jupyter notebooks.
* No inversion of controll, no framework dictating how to code,
  no CLI dependency at all. This is not a code supposed to be
  used via the OS command line but instead in python itself.
* Very simple to install with *NO* dependencies, using only
  python builtins. Advanced codes are, however, integrated
  and can be used if libraries are available at runtime.
  This makes it super easy to get started.
"""

# the four major entrypoints for the library:
from .synchc import LUCIDAC
from .circuits import Circuit, Route, Connection
from .detect import Endpoint, detect
from .simulator import Simulation, Emulation
