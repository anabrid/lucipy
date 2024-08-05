.. lucipy documentation master file, created by
   sphinx-quickstart on Thu Jul 11 11:20:06 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Lucipy: The simple LUCIDAC python client
========================================

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

**Relevant URLs**

Public Development and Releases:

* https://github.com/anabrid/lucipy public development repo
* https://pypi.org/project/lucipy/ python package index listing
* https://anabrid.github.io/lucipy/ sphinx documentation Github Actions generation target (github pages)

Internal Development:

* https://lab.analogparadigm.com/lucidac/software/simplehc.py internal development repo
* https://anabrid.dev/docs/lucipy/ sphinx documentation Gitlab-CI target self-hosted


.. toctree::
   :maxdepth: 2
   :caption: Getting started
   
   installation
   comparison_lucipy_vs_pybrid

.. toctree::
   :maxdepth: 2
   :caption: Circuits
   
   compilation
   lucidac-simulation
   
.. toctree::
   :maxdepth: 2
   :caption: Hardware
   
   endpoint-detection
   connection-sync



Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
