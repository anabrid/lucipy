.. _emu:

LUCIDAC emulation
=================

The LUCIDAC emulation provides python code to mimic the behaviour of a network-enabled LUCIDAC.
That is, any kind of LUCIDAC client can connect to the TCP/IP service provided by the class
:py:class:`~lucipy.simulator.Emulation` and the software does best to try to emulate a "mockup", "virtualized"
or "digital twin" version of the real hardware.

Focus is put on the run simulation which of course makes use of the :ref:`sim` code. Therefore,
in this usage of words, *simulation* is part of the extended concept of *emulation* which also
takes into account the JSONL network protocol API. This protocol API is another way to ensure
the computer model is really constrained to the capabilities of the computer. For instance,
while the :py:class:`~lucipy.simulator.Simulation` class can in principle simulate an unlimited amount
of Routes (and therefore a fully connected system matrix), the protocol ensures that the Emulation
receives only the sparse system matrix configuration.

How to start the emulator
-------------------------

An easy way to start the server is for instance by making up a script,

.. code-block:: python

  #!/usr/bin/env python
  from lucipy import Emulation
  Emulation().serve_forever()


This can be easily adopted, for instance with this advanced version

.. code-block:: python

  #!/usr/bin/env python
  import sys
  from lucipy import Emulation
  Emulation(bind_addr="0.0.0.0", bind_port=int(sys.argv[1])).serve_forever()

This version can be called via ``./start-server.py 1234`` in order to listen on all interfaces
on port ``1234``

General Features
----------------

* Network transparent in the same way as the actual LUCIDAC is. Therefore any kind of client should
  be able to connect.
* Multiprocessing "non-blocking" forking version is readily available, h    owever in this case currently
  each client sees his own emulated and independent LUCIDAC. By default the server is "blocking"
  the same way as early LUCIDAC firmware versions used to do.

Known limitations
-----------------

* Currently emulates only REV0 LUCIDAC hardware with one MInt and one MMul block.
* Very limited support for ACL IN/OUT and ADC IN/OUT. Basically only query based plotting (data
  aquisition) is supported.
* Only a subset of queries is supported. Call ``help`` in order to get a listing. In particular
  no calls with respect to administration/device configuration, login/logout, etc are supported
  for obvious reasons.
* The emulator only speaks the JSONL protocol. If you want to do something more advanced such as
  Websockets and the GUI, you can proxy this service by
  `Lucigo <https://github.com/anabrid/lucigo>`_ (see there also for alternatives).

API Reference
-------------

.. autoclass:: lucipy.simulator.Emulation
   :members:
   :undoc-members:
