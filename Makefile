PYTHON := python3

.NOTPARALLEL:
.PHONY: all clean egg_info release

all: README

clean:
	rm -fr build dist *.egg-info .tox MANIFEST .coverage .cache
	find ./ -name '*.py[co]' -exec rm -f {} \;
	find ./ -depth -name __pycache__ -exec rm -rf {} \;

README: README.md
	echo -e '.. WARNING: AUTO-GENERATED FILE. DO NOT EDIT.\n' > $@
	pandoc --from=markdown --to=rst $< >> $@

egg_info:
	$(PYTHON) setup.py egg_info

release: clean_socket egg_info README
	$(PYTHON) setup.py packages

