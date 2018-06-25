CONF := custodia.conf
PREFIX := /usr
PYTHON := python3
TOX := $(PYTHON) -m tox --sitepackages
DOCS_DIR = docs
SERVER_SOCKET = $(CURDIR)/server_socket
QUICK_GUIDE = docs/source/quick
QUICK_SOCKET = $(QUICK_GUIDE)/quick

RPMBUILD = $(CURDIR)/dist/rpmbuild

VERSION ?= $(shell $(PYTHON) setup.py --quiet version)

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
PYTHONPATH=$(CURDIR)/src $(PYTHON) -Wignore -m custodia.cli \
    --server $(CONTAINER_SOCKET) $$@
endef
export CUSTODIA_CLI_SCRIPT


.NOTPARALLEL:
.PHONY: all clean clean_socket cscope docs lint pep8 test

all: clean_socket lint pep8 test docs
	echo "All tests passed"

clean_socket:
	rm -f $(SERVER_SOCKET) $(CONTAINER_SOCKET) $(QUICK_SOCKET)

clean_coverage:
	rm -f .coverage .coverage.*

lint: clean_socket
	$(TOX) -e lint

pep8: clean_socket
	$(TOX) -e pep8py2
	$(TOX) -e pep8py3

clean: clean_socket clean_coverage
	rm -fr build dist *.egg-info .tox MANIFEST .cache
	rm -f custodia.audit.log secrets.db
	rm -rf docs/build
	find ./ -name '*.py[co]' -exec rm -f {} \;
	find ./ -depth -name __pycache__ -exec rm -rf {} \;
	rm -rf tests/tmp
	rm -rf vol
	rm -f $(QUICK_GUIDE)/quick.audit.log \
	    $(QUICK_GUIDE)/quick.db \
	    $(QUICK_GUIDE)/quick.key

cscope:
	git ls-files | xargs pycscope

test: clean_socket clean_coverage
	$(TOX) --skip-missing-interpreters -e py27-extra,py27-noextra
	$(TOX) --skip-missing-interpreters -e py35-extra,py35-noextra
	$(TOX) --skip-missing-interpreters -e py36-extra,py36-noextra
	$(TOX) --skip-missing-interpreters -e doc
	$(TOX) -e coverage-report

README: README.md
	echo -e '.. WARNING: AUTO-GENERATED FILE. DO NOT EDIT.\n' > $@
	pandoc --from=markdown --to=rst $< >> $@

$(DOCS_DIR)/source/readme.rst: README
	grep -ve '^|Build Status|' < $< | grep -v travis-ci.org > $@

docs: $(DOCS_DIR)/source/readme.rst
	sort $(DOCS_DIR)/source/spelling_wordlist.txt > \
	    $(DOCS_DIR)/source/spelling_wordlist.txt.bak
	mv $(DOCS_DIR)/source/spelling_wordlist.txt.bak \
	    $(DOCS_DIR)/source/spelling_wordlist.txt
	PYTHONPATH=$(CURDIR)/src \
	    $(MAKE) -C $(DOCS_DIR) html SPHINXBUILD="$(PYTHON) -m sphinx"

.PHONY: install egg_info run quickrun packages release releasecheck
install: clean_socket egg_info
	$(PYTHON) setup.py install --root "$(PREFIX)"
	install -d "$(PREFIX)/share/man/man7"
	install -t "$(PREFIX)/share/man/man7" man/custodia.7
	install -d "$(PREFIX)/share/doc/custodia/examples"
	install -t "$(PREFIX)/share/doc/custodia" LICENSE README API.md
	install -t "$(PREFIX)/share/doc/custodia/examples" custodia.conf

egg_info:
	$(PYTHON) setup.py egg_info

packages: egg_info README
	$(PYTHON) setup.py packages
	cd dist && for F in *.gz; do sha512sum $${F} > $${F}.sha512sum.txt; done

release: clean
	@echo "dnf install python3-wheel python3-twine"
	$(MAKE) packages
	@echo -e "\nCustodia release"
	@echo -e "----------------\n"
	@echo "* Upload all release files to github:"
	@echo "  $$(find dist -type f -printf '%p ')"
	@echo "* Upload source dist and wheel to PyPI:"
	@echo "  twine-3 upload dist/*.gz dist/*.whl"

releasecheck: clean
	@ # ensure README is rebuild
	touch README.md
	$(MAKE) README $(DOCS_DIR)/source/readme.rst
	@ # check for version in spec
	grep -q 'version $(VERSION)' custodia.spec || exit 1
	@ # re-run tox
	tox -r
	$(MAKE) packages
	$(MAKE) rpm
	$(MAKE) dockerbuild

run: egg_info
	$(PYTHON) $(CURDIR)/bin/custodia $(CONF)

quickrun: egg_info
	@ # sed -n -e 's/.*\$$ \(alias\|curl\)/\1/p' docs/source/quick.rst
	@ # sed 's,./quick,$(QUICK_SOCKET),g'
	$(PYTHON) bin/custodia $(QUICK_GUIDE)/quick.conf

.PHONY: rpmroot rpmfiles rpm
rpmroot:
	mkdir -p $(RPMBUILD)/BUILD
	mkdir -p $(RPMBUILD)/RPMS
	mkdir -p $(RPMBUILD)/SOURCES
	mkdir -p $(RPMBUILD)/SPECS
	mkdir -p $(RPMBUILD)/SRPMS

rpmfiles: rpmroot packages
	mv dist/custodia-$(VERSION).tar.gz* $(RPMBUILD)/SOURCES
	cp contrib/config/custodia/custodia.conf $(RPMBUILD)/SOURCES/
	cp contrib/config/systemd/system/custodia@.service $(RPMBUILD)/SOURCES/
	cp contrib/config/systemd/system/custodia@.socket $(RPMBUILD)/SOURCES/
	cp contrib/config/tmpfiles.d/custodia.conf $(RPMBUILD)/SOURCES/custodia.tmpfiles.conf

rpm: clean rpmfiles egg_info
	rpmbuild \
	    --define "_topdir $(RPMBUILD)" \
	    --define "version $(VERSION)" \
	    -ba custodia.spec
	echo "$(RPMBUILD)/RPMS"


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

dockerreleasebuild:
	$(MAKE) dockerbuild \
	    DOCKER_BUILD_ARGS="$(DOCKER_RELEASE_ARGS)" \
	    DOCKER_IMAGE="$(DOCKER_IMAGE):$(VERSION)" && \
	echo -e "\n\nRun: $(DOCKER_CMD) push $(DOCKER_IMAGE):$(VERSION)"
