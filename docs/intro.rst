.. _intro:

Introduction
============


``lucipy`` is a Python3 package and demonsrator code to get started with the
`LUCIDAC <https://anabrid.com/luci>`_
analog-digital hybrid computer. With this library, users can program the
network-enabled analog computer straight from the Python programming language.
Lucipy empowers users to integrate analog computers as solvers into their
favourite scientific python environment. In fact the code is focussed on
working with interactively in IPython or Jupyter. This puts it into contrast
to the ``pybrid`` code. See :ref:`comparison` for details.

Lucipy is still in active development and currently provides

* the simple hybrid controller class :py:class:`.LUCIDAC`
* basic syntactic sugar for route-based analog circuit programming with :py:class:`.Circuit`
* Various example codes (basically the
  `analog paradigm application notes <https://analogparadigm.com/documentation.html>`_)
* Routines for device autodiscovery with zeroconf and USB Serial detection

The code was formerly known as "Synchronous Hybrid Controller Python Client for REDAC/LUCIDAC"
(shcpy) and was primarily used for testing protocol extensions and new firmware features. For
instance, the repo also contains an Over-The-Air demo firmware updater.
