# Copyright (C) 2015-2017  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import os
import socket

from custodia.compat import configparser
from custodia.compat import url_escape


CONFIG_SPECIALS = ['authenticators', 'authorizers', 'consumers', 'stores']


def parse_config(args, config):
    """Parse arguments and create basic configuration
    """
    defaults = {
        # Do not use getfqdn(). Internaly it calls gethostbyaddr which might
        # perform a DNS query.
        'hostname': socket.gethostname(),
    }

    parser = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation(),
        defaults=defaults
    )
    parser.optionxform = str

    with args.configfile as f:
        parser.read_file(f)

    for s in CONFIG_SPECIALS:
        config[s] = dict()

    # add env
    parser['ENV'] = {
        k: v.replace('$', '$$') for k, v in os.environ.items()
        if not set(v).intersection('\r\n\x00')}

    # parse globals first
    if parser.has_section('global'):
        for opt, val in parser.items('global'):
            if opt in CONFIG_SPECIALS:
                raise ValueError('"%s" is an invalid '
                                 '[global] option' % opt)
            config[opt] = val

        config['tls_verify_client'] = parser.getboolean(
            'global', 'tls_verify_client', fallback=False)
        config['debug'] = parser.getboolean(
            'global', 'debug', fallback=False)
        if args.debug:
            config['debug'] = True
        config['auditlog'] = os.path.abspath(
            config.get('auditlog', 'custodia.audit.log'))
        config['umask'] = int(config.get('umask', '027'), 8)

        url = config.get('server_url')
        sock = config.get('server_socket')
        if bool(url) == bool(sock):
            raise ValueError("Exactly one of 'server_url' or "
                             "'server_socket' is required.")
        if sock:
            server_socket = os.path.abspath(sock)
            config['server_url'] = 'http+unix://{}/'.format(
                url_escape(server_socket, ''))

    return parser
