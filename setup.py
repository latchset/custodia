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
test_docs_requires = ['docutils', 'markdown']

with open('README') as f:
    long_description = f.read()

setup(
    name='custodia',
    descricription='A service to manage, retrieve and store secrets',
    long_description=long_description,
    version='0.1.90',
    license='GPLv3+',
    maintainer='Custodia project Contributors',
    maintainer_email='simo@redhat.com',
    url='https://github.com/latchset/custodia',
    packages=[
        'custodia',
        'custodia.httpd',
        'custodia.kubernetes',
        'custodia.message',
        'custodia.server',
        'custodia.store',
    ],
    entry_points={
        'console_scripts': [
            'custodia = custodia.server:main'
        ],
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
