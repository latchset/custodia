# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

try:
    # pylint: disable=import-error
    from urllib import quote as url_escape
except ImportError:
    # pylint: disable=no-name-in-module,import-error
    from urllib.parse import quote as url_escape
import importlib
import logging
import os
import sys

# use https://pypi.python.org/pypi/configparser/ on Python 2
from configparser import ConfigParser, ExtendedInterpolation

import pkg_resources

import six

from custodia import log
from custodia.httpd.server import HTTPServer


CONFIG_SPECIALS = ['authenticators', 'authorizers', 'consumers', 'stores']


def source_config():
    if (len(sys.argv) > 1):
        cfgfile = sys.argv[-1]
    elif os.path.isfile('custodia.conf'):
        cfgfile = 'custodia.conf'
    elif os.path.isfile('/etc/custodia/custodia.conf'):
        cfgfile = '/etc/custodia/custodia.conf'
    else:
        raise IOError("Configuration file not found")
    return os.path.abspath(cfgfile)


def attach_store(typename, plugins, stores):
    for name, c in six.iteritems(plugins):
        if getattr(c, 'store_name', None) is None:
            continue
        try:
            c.store = stores[c.store_name]
        except KeyError:
            raise ValueError('[%s%s] references unexisting store '
                             '"%s"' % (typename, name, c.store_name))


def load_plugin(menu, name):
    """Load Custodia plugin

    Entry points are preferred over dotted import path.
    """
    group = 'custodia.{}'.format(menu)
    eps = list(pkg_resources.iter_entry_points(group, name))
    if len(eps) > 1:
        raise ValueError(
            "Multiple entry points for {} {}: {}".format(menu, name, eps))
    elif len(eps) == 1:
        return eps[0].resolve()
    elif '.' in name:
        # fall back to old style dotted name
        module, classname = name.rsplit('.', 1)
        m = importlib.import_module(module)
        return getattr(m, classname)
    else:
        raise ValueError("{}: {} not found".format(menu, name))


def parse_config(cfgfile):
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.optionxform = str

    with open(cfgfile) as f:
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
            name = s
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

        if not parser.has_option(s, 'handler'):
            raise ValueError('Invalid section, missing "handler"')

        handler_name = parser.get(s, 'handler')
        hconf = {'facility_name': s}
        try:
            handler = load_plugin(menu, handler_name)
            classname = handler.__name__
            hconf['facility_name'] = '%s-[%s]' % (classname, s)
        except Exception as e:  # pylint: disable=broad-except
            raise ValueError('Invalid format for "handler" option '
                             '[%r]: %s' % (e, handler_name))

        if handler.options is not None:
            config[menu][name] = handler(parser, s)
        else:
            # old style plugin
            hconf.update(parser.items(s))
            hconf.pop('handler')
            config[menu][name] = handler(hconf)

    # Attach stores to other plugins
    attach_store('auth:', config['authenticators'], config['stores'])
    attach_store('authz:', config['authorizers'], config['stores'])
    attach_store('', config['consumers'], config['stores'])
    attach_store('store:', config['stores'], config['stores'])

    return config


def main():
    cfgfile = source_config()
    config = parse_config(cfgfile)
    log.setup_logging(config['debug'], config['auditlog'])
    logger = logging.getLogger('custodia')
    logger.debug('Config file %s loaded', cfgfile)

    httpd = HTTPServer(config['server_url'], config)
    httpd.serve()
