# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
import argparse
import importlib
import logging
import os
import socket

import pkg_resources

import six

from custodia import log
from custodia.compat import configparser
from custodia.compat import url_escape
from custodia.httpd.server import HTTPServer


logger = logging.getLogger('custodia')
CONFIG_SPECIALS = ['authenticators', 'authorizers', 'consumers', 'stores']


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


def attach_store(typename, plugins, stores):
    for name, c in six.iteritems(plugins):
        if getattr(c, 'store_name', None) is None:
            continue
        try:
            c.store = stores[c.store_name]
        except KeyError:
            raise ValueError('[%s%s] references unexisting store '
                             '"%s"' % (typename, name, c.store_name))


def _load_plugin_class(menu, name):
    """Load Custodia plugin

    Entry points are preferred over dotted import path.
    """
    group = 'custodia.{}'.format(menu)
    eps = list(pkg_resources.iter_entry_points(group, name))
    if len(eps) > 1:
        raise ValueError(
            "Multiple entry points for {} {}: {}".format(menu, name, eps))
    elif len(eps) == 1:
        # backwards compatibility with old setuptools
        ep = eps[0]
        if hasattr(ep, 'resolve'):
            return ep.resolve()
        else:
            return ep.load(require=False)
    elif '.' in name:
        # fall back to old style dotted name
        module, classname = name.rsplit('.', 1)
        m = importlib.import_module(module)
        return getattr(m, classname)
    else:
        raise ValueError("{}: {} not found".format(menu, name))


def _create_plugin(parser, section, menu):
    if not parser.has_option(section, 'handler'):
        raise ValueError('Invalid section, missing "handler"')

    handler_name = parser.get(section, 'handler')
    hconf = {'facility_name': section}
    try:
        handler = _load_plugin_class(menu, handler_name)
        classname = handler.__name__
        hconf['facility_name'] = '%s-[%s]' % (classname, section)
    except Exception as e:  # pylint: disable=broad-except
        raise ValueError('Invalid format for "handler" option '
                         '[%r]: %s' % (e, handler_name))

    if handler._options is not None:  # pylint: disable=protected-access
        # new-style plugin with parser and section
        return handler(parser, section)
    else:
        # old-style plugin with config dict
        hconf.update(parser.items(section))
        hconf.pop('handler')
        return handler(hconf)


def parse_config(args):
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

    config = dict()
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

    # set umask before any plugin gets a chance to create a file
    os.umask(config['umask'])

    for s in parser.sections():
        if s in {'ENV', 'global'}:
            # ENV section is only used for interpolation
            continue

        if s.startswith('/'):
            menu = 'consumers'
            path_chain = s.split('/')
            if path_chain[-1] == '':
                path_chain = path_chain[:-1]
            name = tuple(path_chain)
        else:
            if s.startswith('auth:'):
                menu = 'authenticators'
                name = s[5:]
            elif s.startswith('authz:'):
                menu = 'authorizers'
                name = s[6:]
            elif s.startswith('store:'):
                menu = 'stores'
                name = s[6:]
            else:
                raise ValueError('Invalid section name [%s].\n' % s)

        try:
            config[menu][name] = _create_plugin(parser, s, menu)
        except Exception as e:
            raise RuntimeError(menu, name, e)

    # Attach stores to other plugins
    attach_store('auth:', config['authenticators'], config['stores'])
    attach_store('authz:', config['authorizers'], config['stores'])
    attach_store('', config['consumers'], config['stores'])
    attach_store('store:', config['stores'], config['stores'])

    return config


def main(argparser=None):
    if argparser is None:
        argparser = default_argparser
    args = argparser.parse_args()
    config = parse_config(args)
    log.setup_logging(config['debug'], config['auditlog'])
    logger.debug('Config file %s loaded', args.configfile)
    httpd = HTTPServer(config['server_url'], config)
    httpd.serve()
