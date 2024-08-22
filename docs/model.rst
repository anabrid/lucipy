.. _model:

LUCIDAC model
=============

Lucipy intentionally focusses only on the LUCIDAC. This analog computer is the smallest form of the
REDAC class of computers. In REDAC language, the scope of the LUCIDAC computer is called a
(single) *Cluster*. Furthermore, in this language the motherboard of LUCIDAC is refered to as
*Carrier* (but also "module holder" or "base board"). Contrasting other REDAC variants, LUCIDAC
ships a *front plate* which has analog and digital interfaces as well as a signal generator.

Internally, a single cluster is determined by its interconncetion matrix (also known as *UCI matrix*).
The UCI matrix is an all-to-all matrix connecting 16 analog inputs to 16 analog outputs. The matrix
is spare and can have only up to a few dozen nonzero entries (out of theoretical ``16*16=256``
entries in a full matrix).

See :ref:`lucipy-comp` for a method lucipy provides to describe this kind of circuits. See
:ref:`sim` and :ref:`emu` for ways lucipy provides for digital simulation/emulation of the analog
circuitery and hybrid computer. In particular, see the :ref:`example-circuits` for any kind of
practical ways how to map mathematical problems onto the LUCIDAC computer.

Reconfigurable analog circuit model
-----------------------------------

The focus of this library is on **REV0** LUCIDAC hardware.
What follows is quickly drawn ASCII diagram of this particular
analog computer topology (we have much nicer schemata available which will evventually
replace this one -- TODO: Figure is outdated, for REV0. Must be updated for REV1 or even be replaced
with nicer schematics.):

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
