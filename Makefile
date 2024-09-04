
PYTHON=python3
PYTEST=$(PYTHON) -m pytest

dist:
	rm -fr dist
	python -m build --wheel
	python -m build --sdist
	twine upload dist/*

docs:
	cd docs && make html

doctest:
	$(PYTEST) --doctest-modules --pyargs lucipy -v

unittests: # integration/acceptance tests
	$(PYTEST) -v test/

test:
	$(MAKE) doctest unittests
	
help:
	cat Makefile
	
.PHONY: dist docs test doctest unittests help
