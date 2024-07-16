.. _comparison: 

Comparison LuciPy vs Pybrid
===========================

Reviewing Pybrid from a user perspective
----------------------------------------

Pybrid has three major modes of operation:

* The `click <https://click.palletsprojects.com/>`_ based command line interface which
  can also serve as a small mini DSL for configuration "scripts"
* A framework like variant (somewhat similar to Django) where one defines a class that
  derives from `RunEvaluateReconfigureLoop` with various callbacks. This has to be called
  from the command line as a `user-program`.
* Actual API access which is fully asynchronous and allows to set up all neccessary
  classes on its own.

The CLI looks roughly like this:

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

