.. _model:

LUCIDAC model
=============

Lucipy intentionally focusses only on the LUCIDAC. This analog computer is the smallest form of the
REDAC class of computers. LUCIDAC provides all-to-all connectivity between up to 16 computing
elements with all-to-all connectivity. This is illustrated diagrammatically in the following
figure:

.. image:: figures/system-matrix.*
   :alt: Diagram of the 16x16 interconnection matrix with computing elements at edges

The page :ref:`lucipy-comp` describes the tools lucipy provides to configure this interconnection
matrix as well as stateful computing elements and control circuitery around it. Technically, the
circuit *description* and the computer *steering* are different topics with only a loose
coupling, so users can decide which features they need and which not.

On the reconfigurable analog circuit model
------------------------------------------

.. note::

   An in-depth description of the LUCIDAC hardware is out of scope for this manual. However,
   given the poor overall documentation situation, a short overview is given at this point.

The following figure gives a more detailed overview about the LUCIDAC internals. What is
important to keep in mind that there is a distinguished *compute path* where the analog
signals are traveling (*closed loop*):


.. image:: figures/turbine-diagram.*
   :alt: Turbine diagram showing the different compute elements as little boxes

The following comput elements exist:

- ``M0`` and ``M1`` are *Math blocks*. They each have 16 analog input and 16 analog output
  signals. Math blocks can have arbitrary elements and arbirary digital configuration.
  However, in the first version of LUCIDAC there are only stateless multipliers and stateful
  integrators (see for instance :meth:`~lucipy.circuits.Circuit.int`).
  
  - In Standard LUCIDAC configuration, the Math Block ``M0`` hosts the Integrator block
    ``MIntBlock``. It contains 8 integrators (each 1 input, 1 output). Integrators have
    an internal analog state (the current integration value), digital state (IC/OP/HALT
    state machine) and hybrid state (initial conditions and speed factor).
    
  - In Standard LUCIDAC configuration, the Math Block ``M1`` hosts the Multiplier block
    ``MMulBlock``. It contains 4 multipliers (each 2 input, 1 output). Furthermore, the
    4 leftover outputs are used as constant givers.
- ``ADC``: For data aqusition (ADQ), there are eight 16bit analog-to-digital converters (ADC).
  They have access to all 16 Math block outputs by means of an ``16:8`` analog multiplexer
  (see :meth:`~lucipy.circuits.Probes.measure`).
- ``U`` is the *U-Matrix* and a voltage-coupled ``16:32`` fan-out, allowing to distribute
  the input signals arbitrarily on 16 internal *lanes* within the ``U-C-I`` interconnection
  matrix.
- ``C`` is the *C-Matrix** and implements one coefficient per lane by means of a multiplying
  DAC (basically a digital potentiometer). This allows for scaling the input value within the
  domain ``[-1, +1]``.
- ``I/O`` is a way to feed in/out analog signals to the front panel (``FP``). The last eight
  lanes are always fixed connected to the front panel output. With the ``acl_select``
  property (c.f. :class:`~lucipy.circuits.Probes`), the internal lane signals can be replaced
  by the external input. This can be arbitrary analog signals but also signals from the
  front panel signal generator (``SGEN``) or digital-to-analog converter (``DAC``).
  Note that in REDAC language, this signaling is called ``ACL_IN/OUT`` (short for
  *Analog Cluter* In/Out).
- ``I`` is the *I-Matrix* and a current-coupled ``32:16`` fan-in. It implements implicit
  summation by means of Kirchhoff's law. This naturally maps to the way how a matrix
  multiplication summation works. Thanks to this property, there are no explicit summer
  elements in LUCIDAC.
- ``SH`` is the *Sample & Hold* block. It is transparent for the analog signal path and
  serves for signal conditioning. It is part of the sophisticated error correction method
  applied internally in LUCIDAC.

In the figure shown above ("Turbine diagram"), each thick line represents a vector of 8
analog lines. The digital bus is not shown.

There are various ways how to visualize the internal circuit configuration of a LUCIDAC.
One way is the following ASCII diagram which can be printed by lucipy:

::

    >>> from lucipy import Circuit
    >>> print(Circuit().randomize().to_ascii_art())

    LuciPy LUCIDAC ASCII Dump      +--[ UBlock ]----------------------+
    +-[ M0 = MIntBlock ]-----+     | 0123456789abcdef0123456789abcdef |
    | INT0 IC=-0.07  k0=10^2 | --> 0 X............................... 0
    | INT1 IC=-0.37  k0=10^2 | --> 1 .........X..X..........X..X..... 1
    | INT2 IC=-0.35  k0=10^2 | --> 2 .X....X......................... 2
    | INT3 IC=-0.48  k0=10^2 | --> 3 ..........X..X.............XX... 3
    | INT4 IC=+0.36  k0=10^4 | --> 4 ...X.................X.......... 4
    | INT5 IC=+0.73  k0=10^4 | --> 5 ................X.X............. 5
    | INT6 IC=+0.67  k0=10^4 | --> 6 ....X..........X........X......X 6
    | INT7 IC=-0.82  k0=10^4 | --> 7 ..X...........................X. 7
    +-[ M1 =  MulBlock ]-----+
    | MUL0.a        MUL0.out |  .  8 ................................ 8
    | MUL0.b        MUL1.out | --> 9 ..............X..........X...... 9
    | MUL1.a        MUL2.out | --> A ....................X........... A
    | MUL1.b        MUL3.out | --> B .....X..X........X...........X.. B
    | MUL2.a                 | --> C ...................X............ C
    | MUL2.b                 | --> D ...........X.................... D
    | MUL3.a                 | --> E ......................X......... E
    | MUL3.b                 | --> F .......X........................ F
    +------------------------+     +-vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv-+

                                +--[ CBlock ]----------------------+
                                | 0123456789abcdef0123456789abcdef |
                                    
                                    X||||||||||||||||||||||||||||||| C00 = +2.730 
                                    |X|||||||||||||||||||||||||||||| C01 = -0.761 
                                    ||X||||||||||||||||||||||||||||| C02 = -7.558 
                                    |||X|||||||||||||||||||||||||||| C03 = +9.567 
                                    ||||X||||||||||||||||||||||||||| C04 = +8.500 
                                    |||||X|||||||||||||||||||||||||| C05 = -5.980 
                                    ||||||X||||||||||||||||||||||||| C06 = +4.441 
                                    |||||||X|||||||||||||||||||||||| C07 = -1.105 
                                    ||||||||X||||||||||||||||||||||| C08 = +3.215 
                                    |||||||||X|||||||||||||||||||||| C09 = -7.091 
                                    ||||||||||X||||||||||||||||||||| C10 = +4.700 
                                    |||||||||||X|||||||||||||||||||| C11 = +7.516 
                                    ||||||||||||X||||||||||||||||||| C12 = +1.215 
                                    |||||||||||||X|||||||||||||||||| C13 = +5.657 
                                    ||||||||||||||X||||||||||||||||| C14 = -9.517 
                                    |||||||||||||||X|||||||||||||||| C15 = -6.540 
                                    ||||||||||||||||X||||||||||||||| C16 = -4.744 
                                    |||||||||||||||||X|||||||||||||| C17 = +5.982 
                                    ||||||||||||||||||X||||||||||||| C18 = +1.186 
                                    |||||||||||||||||||X|||||||||||| C19 = +1.559 
                                    ||||||||||||||||||||X||||||||||| C20 = -8.838 
                                    |||||||||||||||||||||X|||||||||| C21 = -6.011 
                                    ||||||||||||||||||||||X||||||||| C22 = +2.143 
                                    |||||||||||||||||||||||X|||||||| C23 = +3.790 
                                    ||||||||||||||||||||||||X||||||| C24 = +3.125 
                                    |||||||||||||||||||||||||X|||||| C25 = -5.170 
                                    ||||||||||||||||||||||||||X||||| C26 = +6.771 
                                    |||||||||||||||||||||||||||X|||| C27 = -4.016 
                                    ||||||||||||||||||||||||||||X||| C28 = +0.872 
                                    |||||||||||||||||||||||||||||X|| C29 = -8.338 
                                    ||||||||||||||||||||||||||||||X| C30 = -5.966 
                                    |||||||||||||||||||||||||||||||X C31 = +0.115 
                                                                    
                                +--[ IBlock ]----------------------+
    +-[ M0 = MIntBlock ]-----+     | 0123456789abcdef0123456789abcdef |
    |                   INT0 | <-- 0 ....X...........X...X........... 0
    |                   INT1 | <-- 1 .................X.............. 1
    |                   INT2 | <-- 2 X..........................X.... 2
    |                   INT3 | <-- 3 ..................X..........X.. 3
    |                   INT4 | <-- 4 ...............X................ 4
    |                   INT5 | <-- 5 ..X................X............ 5
    |                   INT6 | <-- 6 ...X.X...X.X............X.X..... 6
    |                   INT7 | <-- 7 ......X................X........ 7
    +-[ M1 =  MulBlock ]-----+
    |                 MUL0.a | <-- 8 .X.............................X 8
    |                 MUL0.b | <-- 9 .....................XX......... 9
    |                 MUL1.a |  .  A ................................ A
    |                 MUL1.b | <-- B ........X....................... B
    |                 MUL2.a | <-- C ..........X..................... C
    |                 MUL2.b | <-- D ............XX...........X..X... D
    |                 MUL3.a | <-- E ..............X...............X. E
    |                 MUL3.b | <-- F .......X........................ F
    +------------------------+     +----------------------------------+


Beyond LUCIDAC
--------------
   
In REDAC language, the scope of the LUCIDAC computer is called a
(single) *Cluster*. Furthermore, in this language the motherboard of LUCIDAC is refered to as
*Carrier* (but also "module holder" or "base board"). Contrasting other REDAC variants, LUCIDAC
ships a *front plate* which has analog and digital interfaces as well as a signal generator.

Internally, a single cluster is determined by its interconncetion matrix (also known as *UCI matrix*).
The UCI matrix is an all-to-all matrix connecting 16 analog inputs to 16 analog outputs. The matrix
is spare and can have only up to 32 nonzero entries (out of theoretical ``16*16=256``
entries in a full matrix).

See :ref:`lucipy-comp` for a method lucipy provides to describe this kind of circuits. See
:ref:`sim` and :ref:`emu` for ways lucipy provides for digital simulation/emulation of the analog
circuitery and hybrid computer. In particular, see the :ref:`example-circuits` for any kind of
practical ways how to map mathematical problems onto the LUCIDAC computer.

