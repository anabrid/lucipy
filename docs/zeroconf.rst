.. _lucipy-detection:

Endpoints and Autodetection
===========================

*LUCIDAC Endpoints* are URL-like notations for addressing the connection to a
LUCIDAC device. The concept is described in the
`Firmware docs <https://anabrid.dev/docs/hybrid-controller/>`_ and is similar to
the `NI VISA resource syntax <https://www.ni.com/docs/en-US/bundle/ni-visa/page/visa-resource-syntax-and-examples.html>`_

Available endpoints in lucipy
-----------------------------

Which endpoint notation and protocol support is available depends on the client
implementation. Lucipy understands the following endpoints:

USB Serial (virtual terminal) speaking JSONL: ``serial:/``
   A device name is expected afterwards which is immediately passed to the
   `pySerial constructor <https://pyserial.readthedocs.io/en/latest/pyserial_api.html>`_.
   Examples are ``serial://dev/ttyACM0`` on GNU Linux/Mac OS X or ``serial:/COM0`` on
   MS Windows. USB Serial connection is typically error-prone, in particular at startup
   when the buffers still can be filled with old contents. When using the serial
   connection, calls to :meth:`hc.slurp` can help to clear the buffers.

"Raw" TCP/IP speaking JSONL: ``tcp:/``
   This is the native protocol of the LUCIDAC and the most realiable way
   to connect to the LUCIDAC. Typical examples are a Host name
   ``tcp://my-lucidac.local.`` or an IPv4 address ``tcp://192.168.150.229``.
   An optional port can be given, ``tcp://192.168.150.229:5732``.

Integrated Simulator/Emulator: ``emu:/``
   This will *emulate a socket* to the lucipy-integrated LUCIDAC Emulator (see :ref:`emu`). 
   Note that this is also possible by starting the Emulator at another place
   and connecting via something like ``tcp://localhost:1234``. However, this way
   it acts as a shorthand for starting up the emulator at the same time as the
   client, one does not have to transfer the TCP port information. Furthermore, the
   connection does *not* use TCP/IP but is just a python-internal function call
   (this is what was refered to an *emulated socket* in the beginning).
   
   To use this endpoint, just instanciate with ``LUCIDAC("emu:/")``. There are no
   further paths in this URL. However, the optional argument ``?debug`` can be attached
   to start the python debugger if the Emulator crashes.
   
Device autodetection: ``zeroconf:/``
   Use this endpoint string to explicitely use autodetection even in the presence
   of an environment variable ``LUCIDAC_ENDPOINT``. In the same way as ``emu:/``,
   this endpoint URL supports no further arguments.
   
Other endpoints not listed here are explicitely not supported, in particular
websocket and HTTP endpoints. If you need to make use of them, consider using a
proxy such as `lucigo <https://github.com/anabrid/lucigo>`_. In particular, a
typical need is to proxy an USB virtual serial terminal over TCP/IP and there
are many solutions for this listed at the previous link.
 
LUCIDAC autodetection
---------------------
   
For convenience, the :ref:`client code <lucipy-client>` allows for autodetection
of the endpoint using MDNS/Zeroconf. This works by making an instance without
providing the endpoint:

::

   >>> from lucipy import LUCIDAC
   >>> hc = LUCIDAC() # this will trigger the autodetection

Typically, the autodetection connects to the *first* LUCIDAC found in the network
and warns if multiple have been found.   
   
Direct access to the underlying API should not be neccessary, but is possible
with :code:`import lucipy.detect`. The folling reference shows the exposed
functions.

.. note::

   As a design philosophy in *lucipy*, there are no dependencies. Therefore,
   autodetection will only work if you have the 
   `zeroconf <https://python-zeroconf.readthedocs.io/>`_ and/or
   `pySerial <https://pyserial.readthedocs.io/>`_ libraries installed.
   
   If these dependencies are not installed, the code will print warnings suggesting
   you to install them in order to make autodetection work.

Environment variable
--------------------

Conveniently, you can use the operating system environment variable
``LUCIDAC_ENDPOINT``. This can help to keep your scripts clean of volatile,
frequently changing and probably meaningless IP addresses and ports.

Usage is, for instance, in your operating systems shell

::

    export LUCIDAC_ENDPOINT="tcp://10.10.77.123"``
    python some-script-using-luci.py

Note that if you have set the environment variable ``LUCIDAC_ENDPOINT``, this will
effectively overwrite (and thus disable) the autodetection, except you call
``LUCIDAC("zeroconf:/")`` explicitely in your code.

Code refererence
----------------

.. automodule:: lucipy.detect
   :members:
