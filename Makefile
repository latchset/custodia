all: lint pep8 test docs
	echo "All tests passed"

lint:
	# Analyze code
	# don't show recommendations, info, comments, report
	# W0613 - unused argument
	# Ignore cherrypy class members as they are dynamically added
	pylint -d c,r,i,W0613 -r n -f colorized \
		   --notes= \
		   --disable=star-args \
		   ./custodia

pep8:
	# Check style consistency
	pep8 custodia

clean:
	rm -fr build dist *.egg-info
	find ./ -name '*.pyc' -exec rm -f {} \;

cscope:
	git ls-files | xargs pycscope

test:
	pylint -d c,r,i,W0613 -r n -f colorized \
		   --notes= \
		   --disable=star-args \
		   ./tests
	pep8 tests
	rm -f .coverage
	tox

DOCS_DIR = docs
.PHONY: docs

docs:
	$(MAKE) -C $(DOCS_DIR) html
