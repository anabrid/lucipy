.. _intro:

Introduction
============


``lucipy`` is a Python3 package and reference code to get started with the
`LUCIDAC <https://anabrid.com/lucidac>`_
analog-digital hybrid computer. With this library, users can program the
network-enabled analog computer straight from the Python programming language.
Lucipy empowers users to integrate analog computers as solvers into their
favourite scientific python environment. In fact the code is focussed on
working with interactively, for instance in `Jupyter <https://jupyter.org/>_`.

Lucipy is mature and yet in active development. The code currently provides

* the simple hybrid controller class :py:class:`.LUCIDAC`
* a very basic "compiler" for route-based analog circuit programming with :py:class:`.Circuit`
* Various example codes (mostly the
  `analog paradigm application notes <https://analogparadigm.com/documentation.html>`_)
* Routines for device autodiscovery with zeroconf and USB Serial detection

.. note::

   For users new to LUCIDAC, the `Lucidac User documentation <https://anabrid.com/lucidac-user-manual.pdf>`_
   (booklet/PDF) is strongly recommended as an introduction. The scope of this
   documentation is only the lucipy client code and not a general introduction
   into the machine.


Code history: The code was formerly known as "Synchronous Hybrid Controller Python
Client for REDAC/LUCIDAC" (shcpy) and was primarily used for testing protocol
extensions and new firmware features. For instance, the repo also contains an
Over-The-Air demo firmware updater. It coexists with other client implementations
within the LUCIDAC project, for instance the Python library `pybrid`. Currently,
it is suggested to use `lucipy` over `pybrid` because `lucipy` is actively
maintained.
