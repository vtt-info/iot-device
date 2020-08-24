tag:
	git tag ${TAG} -m "${MSG}"
	git push --tags

dist: 
	python3 setup.py sdist bdist_wheel

publish-test: clean dist
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish: clean dist
	twine upload dist/*

test: 
	tox

coverage: test
	coverage report

docs: 
	cd docs; make html
	open docs/_build/html/index.html

clean:
	rm -rf dist
	rm -rf *egg-info