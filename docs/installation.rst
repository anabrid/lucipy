.. _installation: 

Installation
============

As a user, the prefered way is to install *lucipy* with pip:

::

   pip install lucipy

Since there are no dependencies, this goes quick and cannot fail. If you don't want
to or cannot use pip, the code can also be used as with

.. code-block:: bash

   $ git clone https://github.com/anabrid/lucipy.git
   $ cd lucipy
   $ export PYTHONPATH="${PYTHONPATH}:$PWD" # either this
   $ python                                 # or just start your python/scripts from here

Note that the advantage of the second option is that you have the full repository
including the `examples` folder readly available on your computer. If you want to
explore the examples, you need to clone the repository or download a ZIP snapshot
of it from github anway.
   
Getting started as a developer
------------------------------

The recommended way to start as a developer is to work directly on the repository,
for instance with ``pip install -e`` (see `editable installs <https://setuptools.pypa.io/en/latest/userguide/development_mode.html>`_).
If you like virtual environments, this could look like

:: 

  python -m venv foo && source foo/bin/activate # maybe you want to work in a virtual env
  pip install -e git+https://github.com/anabrid/lucipy.git

For further development notes, see :ref:`dev`.


Testing
-------

In order to verify that the lucipy installation you have works, you can use the unit and integration tests
provided by lucipy. Note that tests cannot be run on the pip package but
require the repository checked out. 

We use `Pytest <https://docs.pytest.org>`_ and `doctest <https://docs.python.org/3/library/doctest.html>`_
for testing our codes.
Please inspect the ``Makefile`` in order to see how to invoke the tests. In general,
``make test`` should just get you started.

We extensively use *doctests* because it is great. If you wonder whether to write a doctest or a unit
test, use a doctest. They have a lot of benefits, because they enter the documentation, serve as testing
the stability of the API and are closely related to the code they test. Our unit tests are mainly
*integration tests* which cannot be reasonably covered by doctests.

We can not only test the internals of lucipy such as the API stability of the emulator or the correct
functionality of the simulator, but also can test against real LUCIDAC hardware.
These tests run automatically when the environment
variable ``LUCIDAC_ENDPOINT`` is given. `GNU Make <https://www.gnu.org/software/make/>`_ makes this easy, just call it with, for instance,
``make unittests LUCIDAC_ENDPOINT="tcp://192.168.150.229:5732``.

Here is exemplaric output how running all tests look like. In this example, we set the ``LUCIDAC_ENDPOINT`` environment variable
(see :ref:`lucipy-detection` for details) in order to also run the hardware tests. At the time of writing,
running all tests requires roughly 34 seconds:

::

   you@host .../lucipy (git)-[master] % export LUCIDAC_ENDPOINT="tcp://user:password@123.123.123.123:5732"
   you@host .../lucipy (git)-[master] % make test
   make doctest unittests
   python3 -m pytest --doctest-modules --pyargs lucipy -v
   ==================================================================== test session starts =====================================================================
   platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0 -- /usr/bin/python3
   cachedir: .pytest_cache
   rootdir: /home/sven/Analog/Hardware/lucidac/software/lucipy
   configfile: pyproject.toml
   plugins: typeguard-4.3.0, anyio-4.4.0
   collected 23 items                                                                                                                                           

   lucipy/circuits.py::lucipy.circuits.Circuit PASSED                                                                                                     [  4%]
   lucipy/circuits.py::lucipy.circuits.Circuit.generate PASSED                                                                                            [  8%]
   lucipy/circuits.py::lucipy.circuits.Connection PASSED                                                                                                  [ 13%]
   lucipy/circuits.py::lucipy.circuits.DefaultLUCIDAC.make PASSED                                                                                         [ 17%]
   lucipy/circuits.py::lucipy.circuits.MIntBlock.load PASSED                                                                                              [ 21%]
   lucipy/circuits.py::lucipy.circuits.Reservoir.alloc PASSED                                                                                             [ 26%]
   lucipy/circuits.py::lucipy.circuits.Routing.available_lanes PASSED                                                                                     [ 30%]
   lucipy/circuits.py::lucipy.circuits.Routing.front_input PASSED                                                                                         [ 34%]
   lucipy/circuits.py::lucipy.circuits.Routing.input2output PASSED                                                                                        [ 39%]
   lucipy/circuits.py::lucipy.circuits.Routing.load PASSED                                                                                                [ 43%]
   lucipy/circuits.py::lucipy.circuits.Routing.output2input PASSED                                                                                        [ 47%]
   lucipy/circuits.py::lucipy.circuits.Routing.sanity_check PASSED                                                                                        [ 52%]
   lucipy/circuits.py::lucipy.circuits.Routing.to_dense_matrices PASSED                                                                                   [ 56%]
   lucipy/circuits.py::lucipy.circuits.next_free PASSED                                                                                                   [ 60%]
   lucipy/detect.py::lucipy.detect.Endpoint PASSED                                                                                                        [ 65%]
   lucipy/simulator.py::lucipy.simulator.Emulation PASSED                                                                                                 [ 69%]
   lucipy/simulator.py::lucipy.simulator.Simulation PASSED                                                                                                [ 73%]
   lucipy/simulator.py::lucipy.simulator.Simulation.solve_ivp PASSED                                                                                      [ 78%]
   lucipy/synchc.py::lucipy.synchc.LUCIDAC.resolve_path PASSED                                                                                            [ 82%]
   lucipy/synchc.py::lucipy.synchc.LUCIDAC.set_by_path PASSED                                                                                             [ 86%]
   lucipy/synchc.py::lucipy.synchc.LUCIGroup SKIPPED (all tests skipped by +SKIP option)                                                                  [ 91%]
   lucipy/synchc.py::lucipy.synchc.Run.data SKIPPED (all tests skipped by +SKIP option)                                                                   [ 95%]
   lucipy/synchc.py::lucipy.synchc.Run.next_data SKIPPED (all tests skipped by +SKIP option)                                                              [100%]

   =============================================================== 20 passed, 3 skipped in 0.73s ================================================================
   python3 -m pytest -v test/
   ==================================================================== test session starts =====================================================================
   platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0 -- /usr/bin/python3
   cachedir: .pytest_cache
   rootdir: /home/sven/Analog/Hardware/lucidac/software/lucipy
   configfile: pyproject.toml
   plugins: typeguard-4.3.0, anyio-4.4.0
   collected 26 items                                                                                                                                           

   test/test_circuits.py::test_constant_circuit PASSED                                                                                                    [  3%]
   test/test_emulator.py::test_local_mac PASSED                                                                                                           [  7%]
   test/test_emulator.py::test_mac PASSED                                                                                                                 [ 11%]
   test/test_emulator.py::test_local_config PASSED                                                                                                        [ 15%]
   test/test_emulator.py::test_set_circuit_cluster PASSED                                                                                                 [ 19%]
   test/test_emulator.py::test_set_adc_channels PASSED                                                                                                    [ 23%]
   test/test_emulator.py::test_run_daq PASSED                                                                                                             [ 26%]
   test/test_emulator.py::test_ramp PASSED                                                                                                                       [ 30%]
   test/test_hardware.py::test_empty_configuration PASSED                                                                                                        [ 34%]
   test/test_hardware.py::test_set_circuit_for_cluster PASSED                                                                                                    [ 38%]
   test/test_hardware.py::test_set_adc_channels PASSED                                                                                                           [ 42%]
   test/test_hardware.py::test_ics[-1-False] PASSED                                                                                                              [ 46%]
   test/test_hardware.py::test_ics[-1-True] PASSED                                                                                                               [ 50%]
   test/test_hardware.py::test_ics[-0.5-False] PASSED                                                                                                            [ 53%]
   test/test_hardware.py::test_ics[-0.5-True] PASSED                                                                                                             [ 57%]
   test/test_hardware.py::test_ics[0-False] PASSED                                                                                                               [ 61%]
   test/test_hardware.py::test_ics[0-True] PASSED                                                                                                                [ 65%]
   test/test_hardware.py::test_ics[0.5-False] PASSED                                                                                                             [ 69%]
   test/test_hardware.py::test_ics[0.5-True] PASSED                                                                                                              [ 73%]
   test/test_hardware.py::test_ics[1-False] PASSED                                                                                                               [ 76%]
   test/test_hardware.py::test_ics[1-True] PASSED                                                                                                                [ 80%]
   test/test_simulator.py::test_constant_detection_in_simulation PASSED                                                                                          [ 84%]
   test/test_simulator.py::test_integrator_chain PASSED                                                                                                          [ 88%]
   test/test_simulator.py::test_multipliers PASSED                                                                                                               [ 92%]
   test/test_simulator.py::test_ramp[False] PASSED                                                                                                               [ 96%]
   test/test_simulator.py::test_ramp[True] PASSED                                                                                                                [100%]

   ======================================================================== 26 passed in 34.55s ========================================================================


