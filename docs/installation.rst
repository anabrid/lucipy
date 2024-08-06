.. _installation: 

Getting started with Lucipy
===========================

One day, the prefered way is to install *lucipy* with pip:

::

   pip install lucipy

Since there are no dependencies, this is easy and will always work. If you don't want
to or cannot use pip, the code can also be used as with

.. code-block:: bash

   $ git clone https://github.com/anabrid/lucipy.git
   $ cd lucipy
   $ export PYTHONPATH="${PYTHONPATH}:$PWD" # either this
   $ python                                 # or just start your python/scripts from here

However, **right now** it is **not** recommended to install lucipy over the python
package repository as we don't have stable versions yet. Instead, if you really want to
use pip, you can do it with

:: 

  python -m venv foo && source foo/bin/activate # maybe you want to work in a virtual env
  pip install git+https://github.com/anabrid/lucipy.git


Design principles
-----------------

Lucipy follows a few radical concepts to make it dead-simple to use the code:

* Most of the code works without third party libraries. For instance, you can connect to
  a LUCIDAC via TCP/IP, program a circuit, run it and get the data without any other
  dependency, not even numpy. This makes it dead simple to take the code into use even in
  heterogen and challenging situations, for instance on an old Mac with an old Python
  version.
* Code parts which require dependencies, such as when using the Serial device interface,
  import their dependency at method/function level. This results in a **late** ``ImportError``
  failure, as one can expect from a scripting language.
* Lucipy does **not** ship with a command line executable. Instead, the primary supposed
  interactive usage is via the Python CLI itself. See :ref:`opposite` for the primary
  reason why.
* Lucipy is not designed with performance and excellence in mind. Instead, the driving
  principle is providing a pythonic API which uses as little advanced features as possible.
  Again, see :ref:`opposite` for the primary reason why.

Usage
-----

Here is a typical example how to get started with the code:

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
