.. _dev:

Developer guide
===============

For getting started as a developer, just follow the :ref:`installation` guide.



Technical notes
---------------

Repositories
   We have an internal gitlab with https://lab.analogparadigm.com/lucidac/software/simplehc.py
   where we have tickets. There should be an automatical two way mirroring to 
   https://github.com/anabrid/lucipy. That means you can develop to both repositories.
   Community issues can also take place at https://github.com/anabrid/lucipy/issues.
   
Continous Integration
   Continous Integration (CI) currently happens both at Github and Gitlab. See files ``.gitlab-ci.yml``
   and the directory ``.github/workflows/`` for the relevant configuration files.

   The CI runs the tests, builds the docs and uploads the docs. The CIs at Github and Gitlab do the same,
   in the moment.

Testing
   We use `Pytest <https://docs.pytest.org>`_ and `doctest <https://docs.python.org/3/library/doctest.html>`_
   for testing our codes. Please inspect the ``Makefile`` in order to see how to invoke the tests. In general,
   ``make test`` should just get you started.
   
   We extensively use *doctests* because it is great. If you wonder whether to write a doctest or a unit
   test, use a doctest. They have a lot of benefits, because they enter the documentation, serve as testing
   the stability of the API and are closely related to the code they test. Our unit tests are mainly
   *integration tests* which cannot be reasonably covered by doctests.
   
   We can also test against real LUCIDAC hardware. These tests run automatically when the environment
   variable ``LUCIDAC_ENDPOINT`` is given. GNU Make makes this easy, just call it with, for instance,
   ``make unittests LUCIDAC_ENDPOINT="tcp://192.168.150.229:5732``.

Documentation
   We are using the `Sphinx Documentation <https://www.sphinx-doc.org/>`_ system. You are invited to contribute
   documentation. The usability of code rises and falls with the code documentation provided. This not
   only means full API documentation but also documentation about the reasoning and guiding principles
   and ideas of the developers.

Versioning
   We basically use `semantic versioning <https://semver.org/>`_ but for lazy people. This means we only
   use *minor* and *major*. Instead, the *patch* version is determined automatically from the distance of the
   vcurrent commit to the last tagged version. This is obviously not a good idea if branches are used, but in
   this case people should just use the last stable minor version such as ``1.2.0``, ``1.3.0``, etc. instead
   of ``1.2.14`` or ``1.3.77``.

Releases and Code Deployment
   The package is released at the Python package index manually in the moment, by invoking ``make dist``.
   First, make a ``git tag vX.Y`` and then ``make dist``. Also consider make an annotated tag with 
   release notes.
   
   We don't make Github releases as the time of manually installing
   downloadded `wheels <https://wheel.readthedocs.io/en/latest/>`_ is over.


Strong Design Principles
------------------------

These design principles are in the core of the lucipy design.

Python 3.8 compatibility
   We strieve for *Compatibility with Python 3.8*, released in 2020. Today in 2024, Python 3.8
   is the oldest non end-of-life python version, i.e. still officially
   supported (see `Python release chart <https://devguide.python.org/versions/>`_). We see
   this version still on many computers we regularly become into hands.
   The reason for using this old python version is to make it easier for people to use this code
   even if they don't have the latest operating system installed.
   Our Continous Integration (CI) uses Python 3.8 to make sure backward-compatibility works.

   This means we do not use too new features such as sophisticated typing
   (don't use ``int | str`` but ``Union[Int,Str]``, don't use ``dict[int]`` but ``Dict[Int]``,
   don't use ``None``) or structural pattern matching.
   
Single package and only a few files
   Lucipy is a single python package and all code lives in a single directory. There is nothing
   wrong about a single 1000 lines of code file if it is well structured. Java-esque hierarchies
   of a dozen folders and lot's of tiny almost empty files will not enter lucipy code.

Few imports and classes
   Lucipy is used with a single import statement (``from lucipy import *`` or ``import lucipy``)
   and then provides a *small number* of classes which each have a lot of methods. That means
   rather *broad and flat* API (lot's of methods) instead of a deeply nested hierarchy of structures.
   
   The guiding principle is that the user does not have to write ``from lucipy.foo.bar.baz import Bla``.
   The worst happening is ``from lucipy.foo import Bla`` but it should really be ``from lucipy import Bla``.
   
   This also makes the lucipy API easily explorable from the python REPL (such as ipython).
   
No mandatory dependencies
   All of us went throught python dependency hell (obligatory `XKCD 1987 <https://xkcd.com/1987/>`_),
   isn't it? It can completely prevent users from getting any first step done. It also can
   frighten users to do an upgrade which potentially break things. Better not touch a working virtual
   environment! Well, lucipy goes a different way.
   
   Python already provides everything included to connect to a TCP/IP target. Therefore,
   allow users to getting started without dependencies and import them only when needed, for
   doing the "fancy" things. For instance, there are *many* parts where lucipy needs the
   `numpy <https://numpy.org/>`_ but it *always* includes *in place*, not on a per file level.
   
   Scripts using lucipy can make a different choice, this only relates to the core library files
   defining lucipy.

Focus on scientific python environments
   The primary reason we are working with Python is because the audience of scientists are working
   with Python. This is also the reason why we provided LUCIDAC clients for the
   `Julia Programming Language <https://julialang.org/>`_  and *Matlab* but for instance not Perl or 
   Java. However, scientists are typically not the best programmers. They use python because core python
   has a dead simple syntax. Lucipy tries to be a good citizen in the notebook-centric way of using
   scientific python.

Extensible by default.
   :py:meth:`~lucipy.synchc.LUCIDAC.query` is a perfectly valid way to interact with the
   :py:class:`~lucipy.synchc.LUCIDAC` and to send arbitrary commands. This makes lucipy the
   ideal client for implmenting new LUCIDAC features.

Do not implement a compiler
   We have a number of ongoing projects for implementing a world class differential equations compiler
   for LUCIDAC/REDAC. At the same time there is an urgent need for programming LUCIDAC in a less
   cryptic way then ``route -- 8 0 -1.25 8``. Therefore, the lucipy :py:class:`.Circuit` class and friends
   tries to provide as few code as possible to make this more comfortable, without implementing too
   many logic.
   
Implement the UNIX principle
   *Do one thing and do it good* is the major design goal of lucipy. Any sophisticated task should
   be part of another library. Lucipy does not try to provide the ultimate user experience for
   analog computing. We try to maximize what can be done with the code while keeping it as short as
   possible. Any code not written cannot produce bugs.

Weak Design Principles
----------------------

These design principles will probably change in the future.

Focus only LUCIDAC
   The LUCIDAC computer is part of a bigger project with ambitious targets, the REDAC project.
   Lucipy is only a code for LUCIDAC, not REDAC Since the design of the LUCIDAC is so much simpler
   then the design of the REDAC, it also allows the client code to be dramatically simpler.
   The code does not even try to model advanced REDAC usage patterns but instead
   sticks to the simplicisty of the Model-1 and THAT Hybrid controllers.

Does not reimplement the firmware API
   Lucipy does not try to reimplement the class structure provided by the LUCIDAC Firmware.
   We have python codes which do so (speaking of ``pybrid``) and thus provide ad-hoc RPC
   implementations which is of high maintenance
   since it requires manual labour whenever a change in the upstream API (in the firmware)
   happens. Instead, lucipy looks for a *loose coupling*, making untyped data structures (dicts/lists)
   and JSON a first place citizen.
   Users are encouraged to build such (JSON) objects as needed instead of dealing with class
   hierarchies within Python. A scalable
   answer for a low-maintenance RPC system is without the scope of lucipy, it just tries to
   deal with the existing situation with as little code as possible.

Not a CLI
   For interactive use, lucipy does not have a the command line interfaces (CLIs) as primary interface
   but the python REPL instead. If lucipy will ever provide a CLI, it will be possible to be (also) invoked
   with command such as ``python -m lucipy.foo --bla --bar=5`` instead of an executable like ``lucipy``
   which has to live on your ``$PATH`` (something which, again, requires virtual environments or installations
   and all that)

No async co-routines
   My personal preference is that async gives a terrible programmer's experience
   (I wrote about it: `python co-routines considered bad <https://denktmit.de/blog/2024-07-11-Reductionism-in-Coding/>`_).
   It is also *premature optimization* for some future-pointing high performance message broker
   which does single-threaded work while asynchronously communicating with the REDAC. So
   let's get back to the start and work synchronously, which *dramatically* reduces the
   mental load.

No typing
   There is little advantage of having a loosely typed server (firmware without typed JSON mapping)
   but a strongly typed client (think of ``pybrid`` with `pydantic <https://docs.pydantic.dev/>`_), hosted
   in a loosely typed language such as Python. It also reduces development speed when the
   protocol itself is in change. So for the time being, lucipy does not provide any assistance
   on correctly typed protocol messages. Instead, it intentionally makes it easy to write any kind of
   messages to the microcontroller.

Not a framework
   My personal preference between frameworks and libraries are *always* libraries. Frameworks
   dramatically reduce the freedom of implementing near ideas. I don't see any advantage to provide
   a framework for programming an analog computer.
