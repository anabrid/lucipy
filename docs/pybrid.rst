.. _comparison: 

 --> (This code is supposed to be moved to the pybrid repository/docs)

Comparison with pybrid
======================

Pybrid (`pybrid-computing <https://pypi.org/project/pybrid-computing/>`_) is the reference
implementation for a LUCIDAC client. Development of this code was started around 2022/23
and it implements a sophisticated and future-pointing programming style with
high levels of abstraction, asyncs, context managers, etc. Already early in development,
pybrid put a focus on versioning and dependency managament.

Pybrid was intended as a code to manage different kinds of analog computers from the beginning.
The code was not only supposed to be be the reference client for a novel version of the
Model-1 firmware but also for the hierarchical and digital-distributed REDAC computer.
It has to be stressed that the hardware design for the REDAC was in active development at
the same time pybrid was designed.


Review of pybrid
----------------

This section shall quickly review pybrid **from a user perspective**. For more documentation,
see for instance `the pybrid documentation <https://anabrid.dev/docs/pybrid/html/>`_.
Pybrid has three major modes of operation:

* The `click <https://click.palletsprojects.com/>`_ based command line interface which
  can also serve as a small mini DSL for configuration "scripts"
* A framework like variant (somewhat similar to `Django <https://www.djangoproject.com/>`_)
  where one defines a class that
  derives from ``RunEvaluateReconfigureLoop`` with various callbacks. This has to be called
  from the command line as a ``user-program``.
* Actual library API access which is fully asynchronous and allows to set up all neccessary
  classes on its own.

CLI
...

The command line interface (CLI) for the operating system shell looks roughly like this:

::

    me@ulm-primary:~/lucidac/hybrid-controller$ pybrid --help
    Usage: pybrid [OPTIONS] COMMAND [ARGS]...

    Entrypoint for all functions in the pybrid command line tool.

    Additional :code:`pybrid-computing` packages hook new subcommands into this
    entrypoint. Please see their documentation for additional available
    commands.

    Options:
    --log-level [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                    Set all 'pybrid' loggers to the passed
                                    level.
    --help                          Show this message and exit.

    Commands:
    redac  Entrypoint for all REDAC commands.

The idea is that the code can support different machines. There used to be a `modelone`
variant but now the `redac` argument as first argument is obligatory. Then the options
are

::

    $ pybrid redac --help
    Usage: pybrid redac [OPTIONS] COMMAND [ARGS]...

    Entrypoint for all REDAC commands.

    Use :code:`pybrid redac --help` to list all available sub-commands.

    Options:
    -h, --host TEXT       Network name or address of the REDAC.
    -p, --port INTEGER    Network port of the REDAC.
    --reset / --no-reset  Whether to reset the REDAC after connecting.
                            [default: reset]
    --help                Show this message and exit.

    Commands:
    display             Display the hardware structure of the REDAC.
    get-entity-config   Get the configuration of an entity.
    hack                Collects 'hack' commands, for development purposes...
    reset               Reset the REDAC to initial configuration.
    route               Route a signal on one cluster from one output of...
    run                 Start a run (computation) and wait until it is...
    set-alias           Define an alias for a path in an interactive...
    set-connection      Set one or multiple connections in a U-Block or...
    set-daq             Configure data acquisition of subsequent run commands.
    set-element-config  Set one ATTRIBUTE to VALUE of the configuration of...
    shell               Start an interactive shell and/or execute a REDAC...
    user-program

There is no further explorable help available on the command line.

Here is a usage example to run a harmonic oscillator:

:: 

    # sinusoidal.txt
    # A script for the command line interface,
    # configuring a carrier board to calculate a harmonic oscillator.

    # Set alias for carrier
    set-alias * carrier

    # Configure routing on cluster
    route -- carrier/0 8 0 -1.0 9
    route -- carrier/0 9 1  1.0 8

    # Configure initial condition
    set-element-config carrier/0/M0/0 ic 0.42

    # Configure data acquistion for two channels and 100000 samples/second
    set-daq -n 2 -r 100000

    # Start run and save data
    run --op-time 2560000 --output sinusodial.dat

It is started with

::

    pybrid redac -h redac.lan shell -x sinusoidal.txt
    gnuplot -p -e 'plot "sinusoidal.dat" u ($1/10):2 w l, "" u ($1/10):3 w l'

.. note::
    
   The CLI executable was renamed from ``anabrid`` to ``pybrid`` when the code was
   renamed from ``pyanabrid`` to ``pybrid-computing``
    
Framework
.........

The same example in the framework usage mode was written as

.. code-block:: python

  import matplotlib.pyplot as plt

  from pyanabrid.base.hybrid.programs import SimpleRun
  from pyanabrid.redac import REDAC, Run, RunConfig, DAQConfig


  class UserProgram(SimpleRun):
      # Shortcut to configure run
      RUN_CONFIG = RunConfig(op_time=2_560_000)
      DAQ_CONFIG = DAQConfig(num_channels=2, sample_rate=100_000)

      def set_configuration(self, run: Run, computer: REDAC):
          # Reference to first cluster on first carrier board
          cluster = computer.carriers[0].clusters[0]

          # Configure harmonic oscillator
          cluster.route(8, 0, -1.0, 9)
          cluster.route(9, 1, 1.0, 8)
          # Configure initial value
          cluster.m0block.elements[0].ic = 0.42

      def run_done(self, run: Run):
          # This function is called once the run is done
          if run.data:
              t = [t_/10 for t_ in run.data.pop("t")]
              for channel in run.data.values():
                  plt.plot(t, channel)
              plt.ylabel("Amplitude x")
              plt.xlabel("'Time' t")
              plt.show()
          self.print("Done.")

This file had to be invoked with

:: 

  anabrid redac -h redac.lan user-program sinusodial.py

Note the typical *inversion of control* concept of frameworks which gives very little
flexibility to change control flow but also dramatically reduces the boilerplate code at
the same time. Compare this to the next section (library design pattern).
  
Library
.......

The same problem could be written in an explicit way:

.. code-block:: python

  import asyncio
  import logging

  from matplotlib import pyplot as plt
  from pyanabrid.base.utils.logging import set_pyanabrid_logging_level
  from pyanabrid.base.transport.network import TCPTransport
  from pyanabrid.redac import Protocol, Controller, DAQConfig, RunConfig

  # For development purposes, set all logging to DEBUG
  logging.basicConfig()
  set_pyanabrid_logging_level(logging.DEBUG)

  # Network information of REDAC
  REDAC_HOST = 'redac.lan'
  REDAC_PORT = 5732


  async def main():
      # Create a transport, which handles the underlying network connection.
      transport = await TCPTransport.create(REDAC_HOST, REDAC_PORT)
      # Create a protocol, which handles the message.
      protocol = await Protocol.create(transport)
      # Create a controller, which uses the protocol to execute commands.
      controller = await Controller.create(protocol)
      # Reference for run.
      run = None

      # The controller needs to run through an initialization
      # and de-initialization procedure.
      # To ensure both, it can be used as an async context manager.
      async with controller:
          # First things first, reset the analog computer.
          await controller.reset()

          # The controller detects the elements of the analog computer.
          computer = controller.computer

          # Get a reference to the first cluster on the first carrier.
          cluster = computer.carriers[0].clusters[0]

          # Configure harmonic oscillator on the cluster.
          cluster.route(8, 0, -1.0, 9)
          cluster.route(9, 1, 1.0, 8)
          # Configure initial value.
          cluster.m0block.elements[0].ic = 0.42

          # Upload the changed configuration to the analog computer.
          await controller.set_computer(computer)

          # Create a run and configure it.
          run_config = RunConfig(op_time=2_560_000)
          daq_config = DAQConfig(num_channels=2, sample_rate=100_000)
          run = await controller.create_run(config=run_config, daq=daq_config)

          # Start a run and wait for its result.
          # You can use non-blocking calls and do other work in parallel.
          await controller.start_and_await_run(run)

      # Since we only have one run (calculation), we are done.
      # By exiting the with statement, protocol communication is stopped.

      # Plot data.
      t = [t_ / 10 for t_ in run.data.pop("t")]
      for channel in run.data.values():
          plt.plot(t, channel)
      plt.ylabel("Amplitude x")
      plt.xlabel("'Time' t")
      plt.show()

  asyncio.run(main())

Note how all code has to be written within an async ``main`` method (only IPython
allows to call asynchronous functions directly from the prompt, not ordinary Python).
Also note the usage of the controller class in the context manager.

