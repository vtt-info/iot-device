tag:
	git tag ${TAG} -m "${MSG}"
	git push --tags

dist: 
	python3 setup.py sdist bdist_wheel

publish-test: dist
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish: dist
	twine upload dist/*

test: 
	tox

coverage: test
	coverage report

docs: 
	cd docs; make html
	open docs/_build/html/index.html
