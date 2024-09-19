.. _example-circuits: 

Example circuits
================

This page collects example codes which mainly demonstrate the :ref:`lucipy-comp` machinery
but also touches other parts of the lucipy library.

The examples demonstrate different simple mathematical problems and how to implement
them on LUCIDAC using the *lucipy* software. The examples highlight different parts such as
circuit modeling, digital (numerical) circuit simulation as well as steering the analog computer.

Python scripts
--------------

The following examples are short single file standalone scripts which you can download and
execute if you have lucipy installed. You can find them in the ``examples`` directory of
the lucipy repository.

Simulations
...........

These examples run straight out of the box and demonstrate how to configure a LUCIDAC circuit.
Subsequently, the examples are solved in a digital simulator right within Python and the
result is showed in a plot. Therefore, no hardware is required.

:download:`Rössler <../examples/simulated/roessler.py>`
   Rössler attractor on LUCIDAC, as from 
   `Analog Paradigm Application Note 1 <https://analogparadigm.com/downloads/alpaca_1.pdf>`_.
   Coincidentally, see this example in a very similar notation also in the several-years old
   `PyAnalog FPAA YML <https://github.com/anabrid/pyanalog/blob/master/examples/fpaa-circuits/Alpaca01-Roessler-Attractor.yml>`_.

:download:`Lorenz <../examples/simulated/lorenz.py>`
   Lorenz attractor on LUCIDAC, as from 
   `Analog Paradigm Application Note 2 <https://analogparadigm.com/downloads/alpaca_2.pdf>`_.

:download:`Hindmarsh-Rose <../examples/simulated/hindmarsh-rose-neuron.py>`
   Single Spiking Neuron Model on LUCIDAC, as from 
   `Analog Paradigm Application Note 28 <https://analogparadigm.com/downloads/alpaca_28.pdf>`_.

:download:`Euler spiral <../examples/simulated/euler.py>`
   Euler spiral on LUCIDAC, cf. 
   `Analog Paradigm Application Note 33 <https://analogparadigm.com/downloads/alpaca_33.pdf>`_.
   (Software simulation)

:download:`Sprott SQm system <../examples/simulated/sqm.py>`
   Chaotic Sprott system on LUCIDAC, cf. 
   `Analog Paradigm Application Note 31 <https://analogparadigm.com/downloads/alpaca_31.pdf>`_.
   (Software simulation)

:download:`Yet another chaotic Sprott system <../examples/simulated/sprott.py>`
   Yet another chaotic Sprott system on LUCIDAC, cf. 
   `Analog Paradigm Application Note 43 <https://analogparadigm.com/downloads/alpaca_43.pdf>`_.
   (Software simulation)

:download:`A chaotic system due to Lorenz, 1984 <../examples/simulated/lorenz84.py>`
   A chaotic system due to Lorenz in 1984 on LUCIDAC
   (Software simulation)

:download:`A three-time-scale system <../examples/simulated/ttss.py>`
   A three-time-scale-system on LUCIDAC, cf. 
   `Analog Paradigm Application Note 44 <https://analogparadigm.com/downloads/alpaca_44.pdf>`_.
   (Software simulation)

:download:`A four wing attractor <../examples/simulated/four_wing_attractor.py>`
   A four wing attractor on LUCIDAC.
   (Software simulation)

:download:`The Halvorsen attractor <../examples/simulated/halvorsen.py>`
   The Halvorsen attractor on LUCIDAC.
   (Software simulation)

:download:`The Dadras attractor <../examples/simulated/dadras.py>`
   The Dadras attractor on LUCIDAC.
   (Software simulation)

:download:`The reduced Henon-Heiles attractor <../examples/simulated/rhh.py>`
   The reduced Henon-Heiles attractor on LUCIDAC (cf. Julienn Clinton Sprott,
   "Elegang Chaos - Algebraically Simple Chaotic Flows", World Scientific,
   2016, pp. 133 f.
   (Software simulation)

:download:`The van der Pol oscillator <../examples/simulated/vdp.py>`
    The van der Pol oscillator. (Software simulation)

:download:`Mathieu equation <../examples/simulated/mathieu.py>`
    The Mathieu equation. (Software simulation)

:download:`A Lotka-Volterra system <../examples/simulated/lotka-volterra.py>`
    A Lotka-Volterra system. (Software simulation)

:download:`A hyperjerk system <../examples/simulated/hyperjerk_4.py>`
    A hyperjerk system (with five integrators). (Software simulation)

:download:`A hyperchaotic system including a quartic term <../examples/simulated/hyperchaos.py>`
    A hyperchaotic system including a quartic term. (Software simulation)

Demonstrator applications from booklet
......................................

These examples are part of the `User handbook <https://anabrid.dev/docs/lucidac-user-docs.pdf>`_.
They are basically a subset of the examples given above. You can find them all in the
``examples/rev1-final`` directory. In order to run, they need the ``LUCIDAC_ENDPOINT``
environment variable set and/or a Lucidac connected to USB/the same network. Since most
examples work without data aquisition, you currently cannot run them against the
emulator, i.e. when you use ``LUCIDAC_ENDPOINT="emu://"`` you won't get output.

Jupyter notebooks
-----------------

The following examples are Jupyter/IPython notebooks which combine text/explanations next to
editable and runnable code as well as their (potentially interactive) output, i.e. plots and 
images into single files. They are included into this documentation as "snapshots" and are a
great experience to get started with lucipy.

.. toctree::
   :maxdepth: 2

   examples/simulated/Schroedinger.ipynb
