#!/usr/bin/python
#
# Copyright (C) 2016  Custodia project Contributors, for licensee see COPYING

import sys

import setuptools
from setuptools import setup

SETUPTOOLS_VERSION = tuple(int(v) for v in setuptools.__version__.split("."))


requirements = [
    'custodia >= 0.4.0',
    'ipalib >= 4.5.0',
    'ipaclient >= 4.5.0',
    'six',
]
# test requirements
test_requires = ['coverage', 'pytest']

extras_require = {
    'test': test_requires,
    'test_docs': ['docutils', 'markdown'],
    'test_pep8': ['flake8', 'flake8-import-order', 'pep8-naming'],
    'test_pylint': ['pylint'] + test_requires,
}

# backwards compatibility with old setuptools
# unittest.mock was added in Python 3.3
if SETUPTOOLS_VERSION < (18, 0, 0) and sys.version_info < (3, 3):
    requirements.append('mock')
else:
    extras_require[':python_version<"3.3"'] = ['mock']


with open('README') as f:
    long_description = f.read()


setup(
    name='custodia.ipa',
    description='FreeIPA Vault plugin for Custodia',
    long_description=long_description,
    version='0.4.dev1',
    license='GPLv3+',
    maintainer='Custodia project Contributors',
    maintainer_email='cheimes@redhat.com',
    url='https://github.com/latchset/custodia.ipa',
    namespace_packages=['custodia'],
    package_dir={'': 'src'},
    packages=[
        'custodia.ipa',
    ],
    entry_points={
        'custodia.stores': [
            'IPAVault = custodia.ipa.vault:IPAVault',
            'IPACertRequest = custodia.ipa.certrequest:IPACertRequest'
        ],
        'custodia.authenticators': [
            'IPAInterface = custodia.ipa.interface:IPAInterface',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=requirements,
    tests_require=test_requires,
    extras_require=extras_require,
)
