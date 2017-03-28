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

release: clean egg_info README
	@echo "dnf install python3-wheel python3-twine"
	$(PYTHON) setup.py packages
	cd dist && for F in *.gz; do sha512sum $${F} > $${F}.sha512sum.txt; done
	@echo -e "\ncustodia.ipa release"
	@echo -e "--------------------\n"
	@echo "* Upload all release files to github:"
	@echo "  $$(find dist -type f -printf '%p ')"
	@echo "* Upload source dist and wheel to PyPI:"
	@echo "  twine-3 upload dist/*.gz dist/*.whl"
