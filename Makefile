

dist:
	rm -r dist
	python -m build --wheel
	python -m build --sdist
	twine upload dist/*

docs:
	cd docs && make html

.PHONY = dist docs
