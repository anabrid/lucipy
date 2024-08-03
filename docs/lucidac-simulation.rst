.. _lucipy-sim:

Lucipy Hardware simulation
==========================

Idealized math

loop unrolling
different approaches

Guiding principle of this simulator
-----------------------------------

This Simulator adopts the convention with the column order

::

    M1 Mul
    M0 Int

The basic idea is to relate the standard first order differential equation
:math:`\dot{\vec x} = \vec f(\vec x)` with the LUCIDAC system matrix
:math:`M = UCI` that relates Math-block inputs with Math-block outputs. We
cut the circuit at the analog integrators and identity
:math:`\dot x^{out} = f(x^{in})`. Diagrammatically,

::

       +---> dot x -->[  MInt ]--> x ---+
       |                                |
       |                                |
       +---------...-[ UCI Matrix ]<----+

This feedback network is linearized as in

::

   ic = state^OUT -> U C I -> state^IN -> M -> state^OUT -> ...

In sloppy words this means that :math:`f := M~x^{in}`. However, it is not
as simple as that, because the LUCIDAC also contains non-integrating compute
elements, in particular the multipliers. By splitting the matrix
:math:`M \in \mathbb{R}^{32\times 32}` into four smaller ones
:math:`A, B, C, D \in \mathbb{R}^{16 \times 16}` as in

.. math::

    \begin{pmatrix} M^{in} \\ I^{in} \end{pmatrix}
    = 
    \begin{bmatrix} A & B \\ C & D \end{bmatrix}
    \begin{pmatrix} M^{out} \\ I^{out} \end{pmatrix}

Note how this notation maps implicit summing of the UCI matrix on the summing
property of a matrix multiplication.

We can easily seperate the actual state vector variables :math:`\vec x := I`
from the derived variables :math:`M`. This is done by **loop unrolling**,
which means to compute the effect of the Mul-Block while evaluating :math:`f`.

First, let us write out the vectors

.. math::

    \begin{aligned}
    M^{in} &= \left( M^{in}_{0a}, M^{in}_{0b}, M^{in}_{1a}, M^{in}_{1b}, \dots, M^{in}_{3a} \right) \\
    M^{out} &= \left( M^{out}_0, M^{out}_1, M^{out}_2, M^{out}_3, c_0, c_1, c_2, c_3 \right) \\
    I^{in} &= \left( I^{in}_0, \dots, I^{in}_7 \right) \\
    I^{out} &= \left( I^{out}_0, \dots, I^{out}_7 \right)
    \end{aligned}

This is a definition for REV0 where the superfluous Math block outputs are used
for constant givers :math:`c_i = 1`.

The algorithm is as following: The set of equations is written out as

.. math::

    \begin{aligned}
    M^{in}_i &= A_{ij} ~ M^{out}_j + B_{ij} ~ I^{out}_{ij} \quad&&\text{(eq I)} \\
    I^{in}_i &= C_{ij} ~ M^{out}_j + D_{ij} ~ I^{out}_{ij} \quad&&\text{(eq II)}
    \end{aligned}

and then compute (eq I) :math:`M^{in} = g(I^{out})` with an initial guess :math:`M^{out}=0` and
then iteratively reinserting the solution for :math:`M^{out}`. (eq II) boils then down to
:math:`I^{in} = f(I^{out})` and thus solving the RHS from the beginning.


Alternative simulation approaches
---------------------------------

For sure there are many other ways how one could simulate the LUCIDAC. A few approaches
are presented here with their advantages and disadvantages.

Graph/Netlist simulation
........................

The prefered way of electronics simulation is to set up the actual netlist graph. Given that
the UCI matrix is basically the adjacency matrix for this graph, this is not too hard. One
can then linarize this graph, making it a forest of compute trees each leading to the
computation of a single state variable. Such a linearization can happen at compile time or
at evaluation/run time. The disadvantage of this approach is that the actual matrix structure
of the LUCIDAC is rather lost, in particular the implicit summing structure.


The tensorial simulation approach
.................................

Loop unrolling at compile time results in some tensorial structure (Einstein sum convention
applies)

.. math::

   \begin{aligned}
   I^{in}_i = &\phantom{+} D_{ij} I^{out}_j \\
              &+ E_{ijk} I^{out}_j I^{out}_k \\
              &+ F_{ijkl} I^{...}_j I_k I_l \\
              &+ G_{ijklm} I_j I_k I_l I_m \\
              &+ H_{ijklmn} I_j I_k I_l I_m I_n
   \end{aligned}

Computing E, F, G from A, B, C is definetly possible and would allow for a
"full closed" (yet spare matrix) description of the LUCIDAC. In such a formulation

* :math:`D` collects all linear terms
* :math:`E` collects all quadratic terms (think of :math:`\dot x = xy`), i.e.
  computations that require one multipler.
* :math:`F` collects all terms requiring two multipliers. Think of
  :math:`\dot x = m_2` and :math:`m_2 = x m_1` and :math:`m_1 = x x`.
* :math:`G` collects all terms requiring three multipliers
* :math:`H` collects all terms requiring *all four* multipliers of the system.

Despite :math:`H` is a tensor of rank 6, there are only a handful of realizations of this
matrix possible, given the four multipliers of the system. That means: A lot of indices for
actually performing very little work. Despite a theoretical study, such a "compilation" step
has little advantage. For sure in the numpy model, setting up large spare matrices before doing
a "hot" computation might probably save time. However, the systems for LUCIDAC are nevertheless
so small that no digital computer will have a hard time simulating even in vanilla python.



API Reference
-------------

.. automodule:: lucipy.simulator
   :members:
