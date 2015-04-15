all: lint pep8 test docs
	echo "All tests passed"

lint:
	# Analyze code
	# don't show recommendations, info, comments, report
	# W0613 - unused argument
	# Ignore cherrypy class members as they are dynamically added
	pylint -d c,r,i,W0613 -r n -f colorized \
		   --notes= \
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
	rm -f .coverage
	nosetests -s

DOCS_DIR = docs
.PHONY: docs

docs:
	$(MAKE) -C $(DOCS_DIR) html
