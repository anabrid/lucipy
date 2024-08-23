.. _dev:

Developer notes
===============

For getting started as a developer, just follow the :ref:`installation` guide.

Compatibility
-------------

We have a strong set of guiding principles in the lucipy code (see :ref:`opposite`).
In particular, we want **Compatibility with Python 3.8**, released in 2020.
Today in 2024, Python 3.8 is the oldest non end-of-life python version, i.e. still officially
supported (see `Python release chart <https://devguide.python.org/versions/>`_).
The reason for using this old python version is to make it easier for people to use this code
even if they don't have the latest operating system installed.
Our Continous Integration (CI) uses Python 3.8 to make sure backward-compatibility works.

This means we do not use too new features such as

- sophisticated typing (Union operators, such as ``int | str``, `dict[int]`` or ``None``)
- structural pattern matching

Testing
-------

We use `Pytest <https://docs.pytest.org>`_ and `doctest <https://docs.python.org/3/library/doctest.html>`_
for testing our codes. Please inspect the ``Makefile`` in order to see how to invoke the tests. In general,
``make test`` should just get you started. 

Documentation
-------------

We are using the `Sphinx Documentation <https://www.sphinx-doc.org/>`_ system. You are invited to contribute
documentation.

Versioning
----------

We basically use `semantic versioning <https://semver.org/>`_ but for lazy people. This means we only
use *minor* and *major*. Instead, the *patch* version is determined automatically from the distance of the
current commit to the last tagged version. This is obviously not a good idea if branches are used, but in
this case people should just use the last stable minor version such as ``1.2.0``, ``1.3.0``, etc. instead
of ``1.2.14`` or ``1.3.77``.

Code Deployment
---------------

The package is released at the Python package index manually in the moment, by invoking ``make dist``.

Continous Integration
---------------------

Continous Integration (CI) currently happens both at Github and Gitlab. See files ``.gitlab-ci.yml``
and the directory ``.github/workflows/`` for the relevant configuration files.

The CI runs the tests, builds the docs and uploads the docs. The CIs at Github and Gitlab do the same,
in the moment.
