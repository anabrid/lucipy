.. _installation: 

Getting started with Lucipy
===========================

The prefered way is to install *lucipy* with pip:

::

   pip install lucipy

Since there are no dependencies, this is an easy step.

Lucipy does not ship with a command line executable. Instead, you can make use of the
code straight from python scripts or the python REPL:

::
    
    me@localhost % python
    Python 3.12.3 (main, Apr 23 2024, 09:16:07) [GCC 13.2.1 20240417] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import lucipy
    >>> lucipy.  [tab tab]
    lucipy.Circuit(     lucipy.Endpoint(    lucipy.Route(       lucipy.detect(      
    lucipy.Connection(  lucipy.LUCIDAC(     lucipy.circuits     lucipy.synchc       
    >>> lucipy.detect()
    waiting...
    []

(TODO: Provide a better example)
