#!/usr/bin/python
#
# Copyright (C) 2015  Custodia project Contributors, for licensee see COPYING

from setuptools import setup

requirements = [
    'cryptography',
    'jwcrypto',
    'six',
    'requests']
# configparser; python_version<'3.4'
# extended interpolation is provided by stdlib in Python 3.4+

# extra requirements
k8s_requires = ['docker-py']
etcd_requires = ['python-etcd']

# test requirements
test_requires = ['coverage', 'pytest'] + k8s_requires + etcd_requires
test_pylint_requires = ['pylint'] + test_requires
test_pep8_requires = ['flake8', 'flake8-import-order', 'pep8-naming']
test_docs_requires = ['docutils', 'markdown'] + k8s_requires + etcd_requires

with open('README') as f:
    long_description = f.read()


# Plugins
custodia_authenticators = [
    'SimpleCredsAuth = custodia.httpd.authenticators:SimpleCredsAuth',
    'SimpleHeaderAuth = custodia.httpd.authenticators:SimpleHeaderAuth',
    'SimpleAuthKeys = custodia.httpd.authenticators:SimpleAuthKeys',
    ('SimpleClientCertAuth = '
     'custodia.httpd.authenticators:SimpleClientCertAuth'),
    'K8sNodeAuth = custodia.kubernetes.node:NodeAuth',
]

custodia_authorizers = [
    'SimplePathAuthz = custodia.httpd.authorizers:SimplePathAuthz',
    'UserNameSpace = custodia.httpd.authorizers:UserNameSpace',
    'K8sAuthz = custodia.kubernetes.authz:KubeAuthz',
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
    'EtcdStore = custodia.store.etcdstore:EtcdStore',
    'SqliteStore = custodia.store.sqlite:SqliteStore',
]


setup(
    name='custodia',
    descricription='A service to manage, retrieve and store secrets',
    long_description=long_description,
    version='0.2.dev1',
    license='GPLv3+',
    maintainer='Custodia project Contributors',
    maintainer_email='simo@redhat.com',
    url='https://github.com/latchset/custodia',
    packages=[
        'custodia',
        'custodia.cli',
        'custodia.httpd',
        'custodia.kubernetes',
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
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: Developers',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=requirements,
    tests_require=test_requires,
    extras_require={
        # extended interpolation is provided by stdlib in Python 3.4+
        ':python_version<"3.4"': ['configparser'],
        'etcd_store': etcd_requires,
        'kubernetes': k8s_requires,
        'test': test_requires,
        'test_docs': test_docs_requires,
        'test_pep8': test_pep8_requires,
        'test_pylint': test_pylint_requires,
    },
)
