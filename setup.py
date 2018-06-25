#!/usr/bin/python
#
# Copyright (C) 2015  Custodia project Contributors, for licensee see COPYING
from __future__ import print_function

import os
import sys

import setuptools
from setuptools import Command, setup

SETUPTOOLS_VERSION = tuple(int(v) for v in setuptools.__version__.split("."))


class Version(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print(self.distribution.metadata.version)


about = {}
with open(os.path.join('src', 'custodia', '__about__.py')) as f:
    exec(f.read(), about)


requirements = [
    'cryptography',
    'jwcrypto',
    'six',
    'requests',
]

# extra requirements
gssapi_requires = ['requests-gssapi']
ipa_requires = [
    'ipalib >= 4.5.0',
    'ipaclient >= 4.5.0',
]

# test requirements
test_requires = ['coverage', 'pytest']
test_extras_requires = test_requires + gssapi_requires + ipa_requires

extras_require = {
    'gssapi': gssapi_requires,
    'ipa': ipa_requires,
    'test': test_requires,
    'test_extras': test_extras_requires,
    'test_docs': ['docutils', 'markdown', 'sphinx-argparse',
                  'sphinxcontrib-spelling'] + ipa_requires,
    'test_pep8': ['flake8', 'flake8-import-order', 'pep8-naming'],
    'test_pylint': ['pylint'] + test_extras_requires,
}

# backwards compatibility with old setuptools
# extended interpolation is provided by stdlib in Python 3.4+
# unittest.mock is provided by stdlib in Python 3
if SETUPTOOLS_VERSION < (18, 0, 0) and sys.version_info < (3, 4):
    requirements.extend(['configparser', 'mock'])
else:
    extras_require[':python_version<"3.4"'] = ['configparser', 'mock']


with open('README') as f:
    long_description = f.read()


# Plugins
custodia_authenticators = [
    'IPAInterface = custodia.ipa.interface:IPAInterface',
    'SimpleCredsAuth = custodia.httpd.authenticators:SimpleCredsAuth',
    'SimpleHeaderAuth = custodia.httpd.authenticators:SimpleHeaderAuth',
    'SimpleAuthKeys = custodia.httpd.authenticators:SimpleAuthKeys',
    ('SimpleClientCertAuth = '
     'custodia.httpd.authenticators:SimpleClientCertAuth'),
]

custodia_authorizers = [
    'SimplePathAuthz = custodia.httpd.authorizers:SimplePathAuthz',
    'UserNameSpace = custodia.httpd.authorizers:UserNameSpace',
    'KEMKeysStore = custodia.message.kem:KEMKeysStore',
]

custodia_clients = [
    'KEMClient = custodia.client:CustodiaKEMClient',
    'SimpleClient = custodia.client:CustodiaSimpleClient',
]

custodia_consumers = [
    'Forwarder = custodia.forwarder:Forwarder',
    'Secrets = custodia.secrets:Secrets',
    'Root = custodia.root:Root',
]

custodia_stores = [
    'EncryptedOverlay = custodia.store.encgen:EncryptedOverlay',
    'EncryptedStore = custodia.store.enclite:EncryptedStore',
    'IPAVault = custodia.ipa.vault:IPAVault',
    'IPACertRequest = custodia.ipa.certrequest:IPACertRequest',
    'SqliteStore = custodia.store.sqlite:SqliteStore',
]


setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__summary__'],
    long_description=long_description,
    license=about['__license__'],
    url=about['__uri__'],
    author=about['__author__'],
    author_email=about['__email__'],
    maintainer=about['__author__'],
    maintainer_email=about['__email__'],
    namespace_packages=['custodia'],
    package_dir={'': 'src'},
    packages=[
        'custodia',
        'custodia.cli',
        'custodia.httpd',
        'custodia.ipa',
        'custodia.message',
        'custodia.server',
        'custodia.store',
    ],
    entry_points={
        'console_scripts': [
            'custodia = custodia.server:main',
            'custodia-cli = custodia.cli:main',
        ],
        'custodia.authenticators': custodia_authenticators,
        'custodia.authorizers': custodia_authorizers,
        'custodia.clients': custodia_clients,
        'custodia.consumers': custodia_consumers,
        'custodia.stores': custodia_stores,
    },
    cmdclass={'version': Version},
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=requirements,
    tests_require=test_requires,
    extras_require=extras_require,
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*',
)
