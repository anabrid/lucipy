.. _lucipy-comp:

Circuit notation and Compilation
================================

Lucipy ships with a number of tools to manipulate the LUCIDAC interconnection matrix
(also known as *UCI matrix*).


Reconfigurable analog circuit model
-----------------------------------

The focus of this library is on **REV0** LUCIDAC hardware.
What follows is quickly drawn ASCII diagram of this particular
analog computer topology (we have much nicer schemata available which will evventually
replace this one):

.. only::html

   ::

                                                                           
            ┌───────────────────────      ┌──────────────────────────────┐
            │Math Block M1     m0  0  ->  │U Block                       │
            │4 x Multipliers   m1  1      │16 inputs, fanout on          │
            │2in, 1out each    m2  2      │32 outputs (called lanes)     │
            │                  m3  3      │                              │
      ┌───► │                  .   4 ───► │It is a 16x32 bitmatrix.      │
      │     │constant givers   .   5      │                              │
      │     │                  .   6      │                              │
      │     │                  .   7  ->  │                              │
      │     └───────────────────────      │                              │
      │                                   │                              │
      │     ┌───────────────────────      │                              │
      │     │Math Block M2     i0  8  ->  │                              │
      │     │8 x Integrators   i1  9      │                              │
      │     │1in, 1out each    i2 10      │                              │
      │     │                  i3 11 ───► │                              │
      │  ┌► │                  i4 12      │                              │
      │  │  │            i     i5 13      │                              │
      │  │  │                  i6 14      │                              │
      │  │  │                  i7 15  ->  │                              │
      │  │  └───────────────────────      └──────────────┬───────────────┘
      │  │                                               │                
      │  │                                ┌──────────────▼───────────────┐
      │  │                                │C block.                      │
      │  │                                │32 coefficients               │
      │  │                                │value [-20,+20] each          │
      │  │                                │                              │
      │  │                                └──────────────┬───────────────┘
      │  │                                               │                
      │  │   ┌───────────────────────     ┌──────────────▼───────────────┐
      │  │   │Math Block M1     m0a 0 <-  │I Block                       │
      │  │   │4 x Multipliers   m0b 1     │32 inputs, fanin to           │
      │  │   │2in, 1out each    m1a 2     │16 outputs                    │
      │  │   │                  m1b 3 ◄───┤                              │
      └──┼── │                  m2a 4     │It is a 32x16 bitmatrix       │
         │   │constant givers   m2b 5     │which performs implicit       │
         │   │                  m3a 6     │summation of currents         │
         │   │                  m3b 7 <-  │                              │
         │   └───────────────────────     │                              │
         │                                │                              │
         │   ┌───────────────────────     │                              │
         │   │Math Block M2     i0  8 <-  │                              │
         │   │8 x Integrators   i1  9     │                              │
         │   │1in, 1out each    i2 10     │                              │
         │   │                  i3 11     │                              │
         │   │                  i4 12 ◄───┤                              │
         └───┤                  i5 13     │                              │
            │                  i6 14     │                              │
            │                  i7 15 <-  │                              │
            └───────────────────────     └──────────────────────────────┘

Concept
-------

The main usage shall be demonstrated on the Lorenz attractor example
(see also :ref:`example-circuits`). It can be basically entered as
element connection diagram:


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

Internally, the library stores :py:class:`Route` tuples:

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

By concept, there is **no symbolic representation** but instead
**immediate destruction of any symbolics**. However, the "initial
format" can be easily decompiled:

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

Where :py:func:`Connection` is just a function that generates a :py:class:`Route`.
   
Export formats
--------------

There are various methods available to convert a Routing list to
other representations. First of all, the LUCIDAC sparse JSON configuration format can
be generated:

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

Therefore one can straight forwardly program a LUCIDAC by writing

.. code-block:: python

   from lucipy import LUCIDAC, Circuit
   lorenz = Circuit()
   # ... the circuit from above ...
   
   hc = LUCIDAC()
   hc.set_config(lorenz.generate())
   hc.start_run() # ...

Also other formats can be generated, for instance a single dense 16x16 matrix
showing the interconnects, weights and implict sums between the Math
blocks:

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

This is an export to the ``pybrid`` DSL:

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

See :ref:`example-circuits` for further examples.


API Docs
--------

.. automodule:: lucipy.circuits
   :members:
