CONF := custodia.conf
PREFIX := /usr
PYTHON := python3
TOX := $(PYTHON) -m tox --sitepackages
DOCS_DIR = docs
SERVER_SOCKET = $(CURDIR)/server_socket

DOCKER_CMD = docker
DOCKER_IMAGE = latchset/custodia
DOCKER_RELEASE_ARGS = --no-cache=true --pull=true

CONTAINER_NAME = custodia_container
CONTAINER_VOL = $(CURDIR)/vol
CONTAINER_SOCKET = $(CONTAINER_VOL)/run/sock
CONTAINER_CLI = $(CONTAINER_VOL)/custodia-cli

# helper script for demo
define CUSTODIA_CLI_SCRIPT
#!/bin/sh
set -e
PYTHONPATH=$(CURDIR) $(PYTHON) -Wignore -m custodia.cli \
    --server $(CONTAINER_SOCKET) $$@
endef
export CUSTODIA_CLI_SCRIPT


.NOTPARALLEL:
.PHONY: all clean clean_socket cscope docs lint pep8 test

all: clean_socket lint pep8 test docs
	echo "All tests passed"

clean_socket:
	rm -f $(SERVER_SOCKET) $(CONTAINER_SOCKET)

lint: clean_socket
	$(TOX) -e lint

pep8: clean_socket
	$(TOX) -e pep8py2
	$(TOX) -e pep8py3

clean: clean_socket
	rm -fr build dist *.egg-info .tox MANIFEST .coverage .cache
	rm -f custodia.audit.log secrets.db
	rm -rf docs/build
	find ./ -name '*.py[co]' -exec rm -f {} \;
	find ./ -depth -name __pycache__ -exec rm -rf {} \;
	rm -rf tests/tmp
	rm -rf vol

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

release: clean egg_info README
	@echo "dnf install python3-wheel python3-twine"
	$(PYTHON) setup.py packages
	cd dist && for F in *.gz; do sha512sum $${F} > $${F}.sha512sum.txt; done
	@echo -e "\nCustodia release"
	@echo -e "----------------\n"
	@echo "* Upload all release files to github:"
	@echo "  $$(find dist -type f -printf '%p ')"
	@echo "* Upload source dist and wheel to PyPI:"
	@echo "  twine-3 upload dist/*.gz dist/*.whl"

run: egg_info
	$(PYTHON) -m custodia.server $(CONF)

.PHONY: dockerbuild dockerdemo dockerdemoinit dockershell dockerreleasebuild
dockerbuild:
	rm -f dist/custodia*.whl
	$(PYTHON) setup.py bdist_wheel
	$(DOCKER_CMD) build $(DOCKER_BUILD_ARGS) \
		-f contrib/docker/Dockerfile \
		-t $(DOCKER_IMAGE) .

dockerdemo: dockerbuild
	@mkdir -p -m755 $(CONTAINER_VOL)/lib $(CONTAINER_VOL)/log $(CONTAINER_VOL)/run
	@echo "$$CUSTODIA_CLI_SCRIPT" > $(CONTAINER_CLI)
	@chmod 755 $(CONTAINER_CLI)
	@echo "Custodia CLI: $(CONTAINER_CLI)"

	@$(DOCKER_CMD) rm $(CONTAINER_NAME) >/dev/null 2>&1|| true
	$(DOCKER_CMD) run \
	    --name $(CONTAINER_NAME) \
	    --user $(shell id -u):$(shell id -g) \
	    -e CREDS_UID=$(shell id -u) -e CREDS_GID=$(shell id -g) \
	    -v $(CONTAINER_VOL)/lib:/var/lib/custodia:Z \
	    -v $(CONTAINER_VOL)/log:/var/log/custodia:Z \
	    -v $(CONTAINER_VOL)/run:/var/run/custodia:Z \
	    $(DOCKER_IMAGE):latest \
	    /usr/bin/custodia /etc/custodia/demo.conf

dockerdemoinit:
	$(CONTAINER_VOL)/custodia-cli mkdir /container
	$(CONTAINER_VOL)/custodia-cli set /container/key value
	$(CONTAINER_VOL)/custodia-cli get /container/key

dockershell:
	$(DOCKER_CMD) exec -ti $(CONTAINER_NAME) /bin/bash

dockerrelasebuild:
	VERSION=$$($(PYTHON) -c \
	    "import pkg_resources; print(pkg_resources.get_distribution('custodia').version)") && \
	$(MAKE) dockerbuild \
	    DOCKER_BUILD_ARGS="$(DOCKER_RELEASE_ARGS)" \
	    DOCKER_IMAGE="$(DOCKER_IMAGE):$${VERSION}" && \
	echo -e "\n\nRun: $(DOCKER_CMD) push $(DOCKER_IMAGE):$${VERSION}"
