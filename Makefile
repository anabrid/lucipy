

dist:
	rm -r dist
	python -m build --wheel
	python -m build --sdist
	twine upload dist/*

.PHONY = dist
