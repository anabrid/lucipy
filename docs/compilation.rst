.. _lucipy-comp:

Circuit notation and Compilation
================================

Lucipy ships with a number of tools to manipulate the LUCIDAC interconnection matrix
(also known as *UCI matrix*). In particular, the :mod:`~lucipy.circuits` package provides
a *grammar* for connecting analog computing elements in the LUCIDAC.

A grammar for describing circuits
---------------------------------

The :mod:`~lucipy.circuits` package allows to set up an analog computation circuit with
a number of simple methods which define a "grammar" in terms of a traditional object
oriented "subject verb object" notation. For instance, ``circuit.connect(a,b)`` has the
quite obvious meaning to tell the ``circuit`` to connect ``a`` to ``b``
(see :meth:`~lucipy.Route.connect` for details). Other "literal
methods" are for instance ``circuits.probe(a)`` which tells that ``a`` can be
externally probed with an oscilloscope (see :meth:`~lucipy.Route.probe`)
or ``circuits.measure(a)`` which tells that ``a`` shall be internally measured by the
data acquisition (analog to digital converters, ADCs; see :meth:`~lucipy.Route.measure`).

.. note::

   Note that setting up circuits is, by purpose, intrinsically decoupled from configuring
   the actual hardware. Therefore, when working on a :class:`~lucipy.circuits.Circuit` class as
   in the examples given in the previous paragraph, this **currently** has **no immediate effect**
   on the hardware. Instead, the new analog wiring is only written out when calling the
   :meth:`~lucipy.synchc.LUCIDAC.set_circuit` methods as in ``lucidac.set_circuit(circuit.generate())``.
   
   Future variants of this code may add an *immediate* variant which writes out Routes and
   other configuration as soon as they are defined.


The typical usage of the :class:`~lucipy.circuits.Circuit` class shall be demonstrated on the Lorenz
attractor example (see also :ref:`example-circuits`). It can be basically entered as
element connection diagram :

.. code-block:: python

   from lucipy import Circuit
   
   lorenz = Circuit()

   x   = lorenz.int(ic=-1)
   y   = lorenz.int()
   z   = lorenz.int()
   mxy = lorenz.mul()   # -x*y
   xs  = lorenz.mul()   # +x*s
   c   = lorenz.const()

   lorenz.connect(x,  x, weight=-1)
   lorenz.connect(y,  x, weight=+1.8)
   
   lorenz.connect(x, mxy.a)
   lorenz.connect(y, mxy.b)
   
   lorenz.connect(mxy, z, weight=-1.5)
   lorenz.connect(z,   z, weight=-0.2667)
   
   lorenz.connect(x, xs.a, weight=-1)
   lorenz.connect(z, xs.b, weight=+2.67)
   lorenz.connect(c, xs.b, weight=-1)
   
   lorenz.connect(xs, y, weight=-1.536)
   lorenz.connect(y,  y, weight=-0.1)

Internally, the library stores :py:class:`~lucipy.circuits.Route` tuples:

.. code-block:: python

   >> print(lorenz)
   Routing([Route(uin=8, lane=0, coeff=-1, iout=8),
   Route(uin=9, lane=1, coeff=1.8, iout=8),
   Route(uin=8, lane=2, coeff=1, iout=0),
   Route(uin=9, lane=3, coeff=1, iout=1),
   Route(uin=0, lane=4, coeff=-1.5, iout=10),
   Route(uin=10, lane=5, coeff=-0.2667, iout=10),
   Route(uin=8, lane=14, coeff=-1, iout=2),
   Route(uin=10, lane=15, coeff=2.67, iout=3),
   Route(uin=4, lane=16, coeff=-1, iout=3),
   Route(uin=1, lane=17, coeff=-1.536, iout=9),
   Route(uin=9, lane=18, coeff=-0.1, iout=9),
   Route(uin=8, lane=8, coeff=0, iout=6),
   Route(uin=9, lane=9, coeff=0, iout=6)])

By concept, there is **no (internal) symbolic representation** but instead
*immediate destruction* of any symbolics to the integer indices of what they enumerate
We call this "early compilation" and distinguish it from a "late compilation" which
tries to retain an *intermediate representation* as long as possible. In particular,
this "compiler" does a pick-and-place as soon as possible (not delayed) and thus
intentionally cannot do any kind of *optimization*. It is, after all, intentionally
a very simple compiler which tries to do its scope as good as possible.

The "pseudo-symbolic" input format can be easily "decompiled" with
:meth:`~lucipy.circuits.Routing.reverse`:

.. code-block:: python

   >> print(lorenz.reverse())
   Connection(Int0, Int0, weight=-1),
   Connection(Int1, Int0, weight=1.8),
   Connection(Int0, Mul0.a),
   Connection(Int1, Mul0.a),
   Connection(Mul0, Int2, weight=-1.5),
   Connection(Int2, Int2, weight=-0.2667),
   Connection(Int0, Mul1.a, weight=-1),
   Connection(Int2, Mul1.a, weight=2.67),
   Connection(Const0, Mul1.a, weight=-1),
   Connection(Mul1, Int1, weight=-1.536),
   Connection(Int1, Int1, weight=-0.1),
   Connection(Int0, Mul3.a, weight=0),
   Connection(Int1, Mul3.a, weight=0)

Fundamental building blocks
---------------------------

The fundamental building block of this circuit description language is the
:class:`~lucipy.circuits.Route`. As written in the corresponding API docs, a
:meth:`~lucipy.circuits.Conncetion` is just a function that produces a 
:class:`~lucipy.circuits.Route` which is not yet placed (some codes also refer to
this as "logical routes").

The other fundamental ingredient are actual element descriptions, for instance
for the Integrator (:class:`~lucipy.circuits.Int`) or Multiplier
(:class:`~lucipy.circuits.Mul`). In *lucipy*, these classes always represent
routed "physical" computing elements, i.e. they describe actual and really existing
computing elements. The code currently has no concept for unrouted computing elements.
This makes sense if you keep in mind that by intention this code tries to place early
and allocate on a greedy basis, something which one can do for a simple system such as
LUCIDAC with it's all-to-all connectivity.

A guiding principle at the design of this library was to **minimize the amount of code**
users have to write. This is done by providing *one* big class interface with the
:class:`~lucipy.circuits.Circuit` class which itself inherits a number of more specialized
classes that deal with the particular parts of the hardware model.

Ideally, users have only to import this single class in order to work with the package.
Instances of all classes described in this section can be obtained with various helper methods.
For instance, the :class:`~lucipy.circuits.Reservoir` class does the accounting (greedy place
and routing) and thus hands out instances of the computing elements. This is just one of many
base classes of a :class:`~lucipy.circuits.Circuit`. Other examples are the
:meth:`~lucipy.circuits.Routing.route` and :meth:`~lucipy.circuits.Routing.connect` methods
of the :class:`~lucipy.circuits.Routing` class which hand out (and register)
:class:`~lucipy.circuits.Route` and :meth:`~lucipy.circuits.Conncetion`.
   
Import and Export formats
-------------------------

This section shall provide an overview about the various import and export formats available
in the :mod:`lucipy.circuits` package. In case of an *export*, a method converts
the internal routing list representation to some other, typically equivalent representation.
In case of an *import*, a non-native representation is re-interpreted as a route of lists.

JSON configuration format
.........................

The most important format is the *LUCIDAC protocol* format (see the
`REDAC communication protocol <https://anabrid.dev/docs/hybrid-controller/d1/d1b/protocol.html>`_
in the LUCIDAC/REDAC firmware documentation). It is a sparse JSON format
and lucipy is able to import to and export from this format by emitting or reading the
corresponding python nested dictionary/list data structures which can easily be serialized
to/from JSON with the python-included ``json`` package.

The import form/export to this format is the most important one in the whole package. The
export is provided by :meth:`~lucipy.circuits.Circuit.generate` and the import is provided
by :meth:`~lucipy.circuits.Circuit.load`. Here is an example how to export the Lorenz
circuit given in the sections above:

.. code-block:: python

   >> lorenz.generate()
   {'/U': {'outputs': [8,
      9,
      8,
      9,
      0,
      10,
      None,
      None,
      8,
      9,
      None,
      None,
      None,
      None,
      8,
      10,
      4,
      1,
      9,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None]},
   '/C': {'elements': [-1,
      1.8,
      1,
      1,
      -1.5,
      -0.2667,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      -1,
      2.67,
      -1,
      -1.536,
      -0.1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0]},
   '/I': {'outputs': [[2],
      [3],
      [14],
      [15, 16],
      [],
      [],
      [8, 9],
      [],
      [0, 1],
      [17, 18],
      [4, 5],
      [],
      [],
      [],
      [],
      []]},
   '/M0': {'elements': [{'k': 10000, 'ic': -1},
      {'k': 10000, 'ic': 0},
      {'k': 10000, 'ic': 0},
      {'k': 10000, 'ic': 0.0},
      {'k': 10000, 'ic': 0.0},
      {'k': 10000, 'ic': 0.0},
      {'k': 10000, 'ic': 0.0},
      {'k': 10000, 'ic': 0.0}]},
   '/M1': {}}


This makes it easy to straight forwardly program a LUCIDAC by writing

.. code-block:: python

   from lucipy import LUCIDAC, Circuit
   lorenz = Circuit()
   # ... the circuit from above ...
   
   hc = LUCIDAC()
   hc.set_config(lorenz.generate())
   hc.start_run() # ...


Numpy matrix formats
....................

A single 16x16 interconnect matrix ``A`` can be generated which describes the
system interconnection in a traditional matrix scheme ``inputs = A * outputs``,
see :ref:`sim` for details.

This matrix incorporates the interconncets, weights and implicit sums between Math
blocks. It can not properly represent the external I/O. Usage requires
the ``numpy`` package. What follows is a usage example:

.. code-block:: python

   >> import numpy as np
   >> np.set_printoptions(edgeitems=30, linewidth=1000, suppress=True)
   >> lorenz.to_dense_matrix().shape
   (16,16)
   >> lorenz.to_dense_matrix()
   array([[ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  1.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  1.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    , -1.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    , -1.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  2.67  ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    , -1.    ,  1.8   ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    , -1.536 ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    , -0.1   ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [-1.5   ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    , -0.2667,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ],
          [ 0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ,  0.    ]])

Other formats exist, for instance to export the internal U, C and I
matrices seperately.


pybrid interface
................

This is an export to the ``pybrid`` DSL (see :ref:`comparison` for details):

.. code-block:: python

   >> print(lorenz.to_pybrid_cli())
   set-alias * carrier

   set-element-config carrier/0/M0/0 ic -1
   set-element-config carrier/0/M0/0 k -1
   set-element-config carrier/0/M0/1 k 0
   set-element-config carrier/0/M0/2 k 0
   set-element-config carrier/0/M0/3 k 0.0
   set-element-config carrier/0/M0/4 k 0.0
   set-element-config carrier/0/M0/5 k 0.0
   set-element-config carrier/0/M0/6 k 0.0
   set-element-config carrier/0/M0/7 k 0.0
   route -- carrier/0  8  0  -1.000  8
   route -- carrier/0  9  1   1.800  8
   route -- carrier/0  8  2   1.000  0
   route -- carrier/0  9  3   1.000  1
   route -- carrier/0  0  4  -1.500 10
   route -- carrier/0 10  5  -0.267 10
   route -- carrier/0  8 14  -1.000  2
   route -- carrier/0 10 15   2.670  3
   route -- carrier/0  4 16  -1.000  3
   route -- carrier/0  1 17  -1.536  9
   route -- carrier/0  9 18  -0.100  9
   route -- carrier/0  8  8   0.000  6
   route -- carrier/0  9  9   0.000  6
   # run --op-time 500000

Sympy interface
...............

Here comes an export to a Sympy system:

.. code-block:: python

   >> lorenz.to_sympy()
   [Eq(m_0(t), -i_0(t)*i_1(t)),
   Eq(m_1(t), (2.67*i_2(t) - 1.0)*i_0(t)),
   Eq(Derivative(i_0(t), t), -i_0(t) + 1.8*i_1(t)),
   Eq(Derivative(i_1(t), t), -0.1*i_1(t) - 1.536*m_1(t)),
   Eq(Derivative(i_2(t), t), -0.2667*i_2(t) - 1.5*m_0(t))]

This can be tailored in order to have something which can be straightforwardly
numerically solved:

.. code-block:: python

   >> [ eq.rhs for eq in lorenz.to_sympy(int_names="xyz", subst_mul=True, no_func_t=True) ]
   [-x + 1.8*y, -1.536*x*(2.67*z - 1.0) - 0.1*y, 1.5*x*y - 0.2667*z]


Random system generation
........................

For testing and documentation purposes, there is :meth:`Circuit.random` which creates random
routes. This simplifies writing unit tests (see also :ref:`dev`).

API Docs
--------

.. automodule:: lucipy.circuits
   :members:
