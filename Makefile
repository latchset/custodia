all: lint pep8 test docs
	echo "All tests passed"

lint:
	tox -e lint

pep8:
	tox -e pep8

clean:
	rm -fr build dist *.egg-info .tox
	rm -f server_socket
	find ./ -name '*.py[co]' -exec rm -f {} \;
	find ./ -depth -name __pycache__ -exec rm -rf {} \;
	rm -rf tests/tmp

cscope:
	git ls-files | xargs pycscope

test:
	pylint -d c,r,i,W0613 -r n -f colorized \
		   --notes= \
		   --disable=star-args \
		   ./tests
	rm -f .coverage
	tox -e py27
	tox -e py34

DOCS_DIR = docs
.PHONY: docs

docs:
	$(MAKE) -C $(DOCS_DIR) html
