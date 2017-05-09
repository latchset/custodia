# Copyright (C) 2015-2017  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import argparse


default_argparser = argparse.ArgumentParser(
    prog='custodia',
    description='Custodia server'
)
default_argparser.add_argument(
    '--debug',
    action='store_true',
    help='Debug mode'
)
default_argparser.add_argument(
    'configfile',
    nargs='?',
    type=argparse.FileType('r'),
    help='Path to custodia server config',
    default='/etc/custodia/custodia.conf'
)
