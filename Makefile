PY34 := $(shell python3.4 -V >/dev/null 2>&1 && echo "YES" || echo "NO")
PY35 := $(shell python3.5 -V >/dev/null 2>&1 && echo "YES" || echo "NO")

.NOTPARALLEL:
.PHONY: all clean cscope docs lint pep8 test

all: lint pep8 test docs
	echo "All tests passed"

lint:
	tox -e lint

pep8:
	tox -e pep8py2
	tox -e pep8py3

clean:
	rm -fr build dist *.egg-info .tox MANIFEST .coverage .cache
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
	@# Use --skip-missing-interpreters once we can move past tox 1.8.1
	@# which apparently fails to actually skip a missing interpreter.
ifeq ($(PY34),YES)
	tox -e py34
endif
ifeq ($(PY35),YES)
	tox -e py35
endif

DOCS_DIR = docs

docs:
	$(MAKE) -C $(DOCS_DIR) html
