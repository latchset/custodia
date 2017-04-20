#!/usr/bin/python
#
# Copyright (C) 2016  Custodia project Contributors, for licensee see COPYING

from setuptools import setup

requirements = [
    'custodia >= 0.3.1',
    'ipalib >= 4.5.0',
    'ipaclient >= 4.5.0',
    'six',
]
# test requirements
test_requires = ['coverage', 'pytest', 'mock']
test_pylint_requires = ['pylint'] + test_requires
test_pep8_requires = ['flake8', 'flake8-import-order', 'pep8-naming']


with open('README') as f:
    long_description = f.read()


setup(
    name='custodia.ipa',
    description='FreeIPA Vault plugin for Custodia',
    long_description=long_description,
    version='0.3.dev1',
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
    extras_require={
        'test': test_requires,
        'test_docs': ['docutils', 'markdown'],
        'test_pep8': test_pep8_requires,
        'test_pylint': test_pylint_requires,
    },
)
