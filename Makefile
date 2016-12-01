CONF := custodia.conf
PREFIX := /usr
PYTHON := python3
TOX := $(PYTHON) -m tox --sitepackages
DOCS_DIR = docs

.NOTPARALLEL:
.PHONY: all clean clean_socket cscope docs lint pep8 test

all: clean_socket lint pep8 test docs
	echo "All tests passed"

clean_socket:
	rm -f server_socket

lint: clean_socket
	$(TOX) -e lint

pep8: clean_socket
	$(TOX) -e pep8py2
	$(TOX) -e pep8py3

clean: clean_socket
	rm -fr build dist *.egg-info .$(TOX) MANIFEST .coverage .cache
	rm -f custodia.audit.log secrets.db
	rm -rf docs/build
	find ./ -name '*.py[co]' -exec rm -f {} \;
	find ./ -depth -name __pycache__ -exec rm -rf {} \;
	rm -rf tests/tmp

cscope:
	git ls-files | xargs pycscope

test: clean_socket
	rm -f .coverage
	$(TOX) --skip-missing-interpreters -e py27
	$(TOX) --skip-missing-interpreters -e py34
	$(TOX) --skip-missing-interpreters -e py35
	$(TOX) --skip-missing-interpreters -e doc

README: README.md
	echo -e '.. WARNING: AUTO-GENERATED FILE. DO NOT EDIT.\n' > $@
	pandoc --from=markdown --to=rst $< >> $@

$(DOCS_DIR)/source/readme.rst: README
	grep -ve '^|Build Status|' < $< | grep -v travis-ci.org > $@

docs: $(DOCS_DIR)/source/readme.rst
	$(MAKE) -C $(DOCS_DIR) html

.PHONY: install egg_info run release
install: clean_socket egg_info
	$(PYTHON) setup.py install --root "$(PREFIX)"
	install -d "$(PREFIX)/share/man/man7"
	install -t "$(PREFIX)/share/man/man7" man/custodia.7
	install -d "$(PREFIX)/share/doc/custodia/examples"
	install -t "$(PREFIX)/share/doc/custodia" LICENSE README API.md
	install -t "$(PREFIX)/share/doc/custodia/examples" custodia.conf

egg_info:
	$(PYTHON) setup.py egg_info

release: clean_socket egg_info README
	$(PYTHON) setup.py packages

run: egg_info
	$(PYTHON) -m custodia.server $(CONF)
