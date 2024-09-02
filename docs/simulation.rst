.. _sim:

Circuit simulation
==================

Lucipy ships two approaches to simulate a circuit configuration which both
solve circuit as a first order differential equation system using idealized
math elements.

* The method :py:meth:`.Routing.to_sympy` provides an export to a system of
  equations written symbolically, translating the analog circuit to its idealized
  math counterpart. This system can then be solved analytically
  or numerically.
* The class :py:class:`.Simulation` does something similar but without making use of
  Sympy, instead directly working on the UCI matrix. It computes the right hand side
  function by *loop unrolling* the LUCIDAC multipliers.

Both approaches are currently limited to the LUCIDAC standard configuration
of Math block elements. This section concentrates on the approach provided
by :py:class:`.Simulation`. Furher approaches are discussed in the section
:ref:`sim-variants`.

Frequent issues when using the Simulator
----------------------------------------

Misunderstanding Scipy's solve_ivp
..................................

Note that scipy's `solve_ivp <https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html>`_
might lead to surprising results if you never used
it before. In order to not misinterpret the results, a few rules should be kept
in mind:

First of all, the ODE solver can fail. Typical examples are ill-configured circuits/equations
where infinite values and NaNs enter the simulation domain. Therefore, before
looking into other errors, better first check the ``status`` field in the result:

::

  res = Simulation(circuit).solve_ivp(t_final)
  assert res.status == 0, "ODE solver failed"
  assert res.t[-1] == t_final

Second, ``solve_ivp`` uses method for automatically determining the ideal time step sizes
adaptively. Normally this is very clever and thus provides only a small number of
support points within the domain. Therefore, you are urged to use the ``res.t`` field to
get an idea of the times where the solution vector ``res.y`` is defined on. In particular,
a frequent mistake is a matplotlib command such as

::

   plot(res.y[0])

which will do linear interpolation between the support points. In problems where ``solve_ivp``
could optimize a lot, this will yield very wrong looking results. Instead, plot at least
with

::

  plot(res.t, res.y[0], "o-")

but ideally, you want to use the ``dense_output`` interpolation property of the ``solve_ivp``
code. Consider this example:
    
    
.. plot::
  :include-source:

  from lucipy import Circuit, Simulation
  import matplotlib.pyplot as plt
  import numpy as np

  c = Circuit()
  i0, i1, i2 = c.ints(3)
  cnst = c.const()
  c.connect(cnst, i0, weight=-1)
  c.connect(i0, i1, weight=-2)
  c.connect(i1, i2, weight=-3)

  res = Simulation(c).solve_ivp(1, dense_output=True)

  p0 = plt.plot(res.t, res.y[0], "o--", label="$t$")
  p1 = plt.plot(res.t, res.y[1], "o--", label="$t^2$")
  p2 = plt.plot(res.t, res.y[2], "o--", label="$t^3$")
  
  t = np.linspace(0, 1)  # a "denser" array of times
  densey = res.sol(t) # interpolated solution on denser time
  
  plt.plot(t, densey[0], color=p0[0].get_color())
  plt.plot(t, densey[1], color=p1[0].get_color())
  plt.plot(t, densey[2], color=p2[0].get_color())
  
  plt.title("Computing polynoms with LUCIDAC")
  plt.xlabel("Simulation time")
  plt.ylabel("Analog units")
  plt.legend()

The little demonstration computed a few powers of the linear curve $f(t)=t$ by chaining
a few integrators. 
In this extreme example, the three signals show each the naively interpolated solution
(dashed line) on the few support points (dots). They are, however, completely different
then the actual solution (solid lines).
  

Getting access to further system properties
...........................................

The simulator always keeps all 8 integrators as the system state. That means
the solution vector ``y`` in the object returned by ``solve_ivp`` is always of
shape ``(8, num_solution_points)``.

Despite it can be handy to index this by the computing elements defined before,
as in

::

   circuit = Circuit()
   i = circuit.int()
   m = circuit.mul()
   
   # actual circuit skipped in this example
   
   res = Simulation(circuit).solve_ivp(some_final_time)
   evolution_for_i = res.y[i.id] # this works
   evolution_for_m = res.y[m.id] # this does NOT work!

Note how ``i.id`` only resolves to an index which "by coincidence" is within the
range ``[0,8]`` which both are fine for addressing within the MIntBlock and the 
solution vector.

However, ``m.id`` also resolves to such an index which is however meaningless when
applied to the MIntBlock! Since the unused integrators in the simulation have a
zero input, their output is always zero (``0.0``) and thus the resulting error
might assume that the multiplier results in zero output, which is a wrong
interpretation!

The correct way to get access to the multipliers is the
:meth:`~lucipy.simulator.Simulation.Mul_out` method, i.e. in this way:

::

   circuit = Circuit()
   i = circuit.int()
   m = circuit.mul()
   
   # actual circuit skipped in this example
   
   sim = Simulation(circuit)
   res = sim.solve_ivp(some_final_time)
   evolution_for_i = res.y[i.id] # this works
   evolution_for_m = [ sim.Mul_out(ryt)[m.id] for ryt in res.y.T ] # this works

Similar mapping methods available to obtain the computer state, derived from the
integrator state, exist, such as

- :meth:`~lucipy.simulator.Simulation.adc_values`: Obtain the output of the eight ADCs.
- :meth:`~lucipy.simulator.Simulation.acl_out_values`: Obtain the output at the front
  panel (``ACL_OUT``).
- :meth:`~lucipy.simulator.Simulation.mblocks_output`: Obtain the output of all two
  MBlocks, i.e. both the integrator and the multiplier in a single array.

Note that if you decide to use the Emulator API, you will always only get access to the
ADC values, the same way as in a real LUCIDAC.


Guiding principle of this simulator
-----------------------------------

This Simulator adopts the convention with the column order

::

    M0 = Integrator Block (8 Integrators)
    M1 = Multiplier Block (4 Multipliers, 4 identity elements)

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

    \begin{pmatrix} I^{in} \\ M^{in} \end{pmatrix}
    = 
    \begin{bmatrix} A & B \\ C & D \end{bmatrix}
    \begin{pmatrix} I^{out} \\ M^{out} \end{pmatrix}

Note how this notation maps implicit summing of the UCI matrix on the summing
property of a matrix multiplication.

We can easily seperate the actual state vector variables :math:`\vec x := I`
from the derived variables :math:`M`. This is done by **loop unrolling**,
which means to compute the effect of the Mul-Block while evaluating :math:`f`.

First, let us write out the vectors

.. math::

    \begin{aligned}
    M^{in} &= \left( M^{in}_{0a}, M^{in}_{0b}, M^{in}_{1a}, M^{in}_{1b}, \dots, M^{in}_{3a} \right) \\
    M^{out} &= \left( M^{out}_0, M^{out}_1, M^{out}_2, M^{out}_3, M^{in}_{0a}, M^{in}_{0b}, M^{in}_{1a}, M^{in}_{1b} \right) \\
    I^{in} &= \left( I^{in}_0, \dots, I^{in}_7 \right) \\
    I^{out} &= \left( I^{out}_0, \dots, I^{out}_7 \right)
    \end{aligned}

This is a definition for REV0 where the superfluous Math block outputs are used
for identity elements.

The algorithm is as following: The set of equations is written out as

.. math::

    \begin{aligned}
    I^{in}_i &= A_{ij} ~ I^{out}_j + B_{ij} ~ M^{out}_{ij} \quad&&\text{(eq I)} \\
    M^{in}_i &= C_{ij} ~ I^{out}_j + D_{ij} ~ M^{out}_{ij} \quad&&\text{(eq II)}
    \end{aligned}

and then compute (eq I) :math:`M^{in} = g(I^{out})` with an initial guess :math:`M^{out}=0` and
then iteratively reinserting the solution for :math:`M^{out}`. (eq II) boils then down to
:math:`I^{in} = f(I^{out})` and thus solving the RHS from the beginning.


.. _sim-variants:

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

Including imperfection
......................

A first option to model the non-idealities of analog computing hardware is to introduce
*transfer functions* which model what computing elements are doing. We have a Matlab/Simulink 
simulator available which uses this kind of modeling. More realistic models are available with
*Spice* but require to describe both the reconfigurable hardware as well as its configuration
within Spice. However, we provide software to generate these files soon.


API Reference
-------------

.. autoclass:: lucipy.simulator.Simulation
   :members:
   :undoc-members:
