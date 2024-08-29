.. _usage:

Basic patterns and usage
========================

This page gives an introductory overview about how the code can be used to solve common
problems. This shall not replace a general introduction about the LUCIDAC computer and its
abilities. This can be read in the *lucidoc* end user documentation (to be linked here
as PDF once it is ready).

Circuit configuration
---------------------

The typical first time user experience of lucipy is to run a few of the :ref:`example-circuits`.
They all follow the same schema:

#. Construct :class:`~lucipy.circuits.Circuit`
#. Connect to :class:`~lucipy.synchc.LUCIDAC` and configure/upload the circuit
#. Start run, do data aquisition
#. Visualize data

Parameter study
---------------

In order to do a parameter study, one wants to loop the previously described process.
Many "unit test cases" provided in the repository do this in order to aquire a lot of data.

It is possible to alter only parts of the configuration and send them, for instance by using
the :meth:`~lucipy.synchc.LUCIDAC.set_by_path` method of :class:`~lucipy.synchc.LUCIDAC`.
This, however, requires some understanding of the
`entity concept <https://anabrid.dev/docs/hybrid-controller/de/dfd/entities.html>`_ of LUCIDAC.
This can probably speed up the configuration process a bit.

Data aquisition and Manual Steering
-----------------------------------

For interactive sessions with an oscilloscope, it can be very interesting to decouple the
integrated analog-to-digital data aquisition from the analog computer operating mode, i.e.
the simple state machine `IC -> OP -> HALT`. The method
:meth:`~lucipy.synchc.LUCIDAC.manual_mode` is suitable for steering this mode for instance
from the python prompt or within a script. Note that this is far from allowing real time
control.

At the other hand, data aquisition can be triggered manually with the
:meth:`~lucipy.synchc.LUCIDAC.one_shot_daq` call, which will return a single sample of the
eight ADC samples.

Master/Minion multi-device use
------------------------------

The :class:`~lucipy.synchc.LUCIGroup` allows for steering multiple LUCIDACs in one go. For
having precisely locked state machines, this requires a digital front panel connection.
