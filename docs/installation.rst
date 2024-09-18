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

