#!/usr/bin/python
#
# Copyright (C) 2015  Custodia project Contributors, for licensee see COPYING

from distutils.core import setup

setup(
    name = 'custodia',
    version = '0.0.1',
    license = 'GPLv3+',
    maintainer = 'Custodia project Contributors',
    maintainer_email = 'simo@redhat.com',
    url='https://github.com/simo5/custodia',
    packages = ['custodia', 'custodia.tools'],
    data_files = [('share/man/man7', ["man/custodia.7"]),
                  ('share/doc/custodia', ['COPYING', 'README']),
                  ('share/doc/custodia/examples', ['examples/custodia.conf']),
                 ],
    scripts = ['custodia/custodia']
)

