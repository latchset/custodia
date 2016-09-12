# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
import argparse
import logging
import os
import sys
import traceback

try:
    # pylint: disable=import-error
    from urllib import quote as url_escape
except ImportError:
    # pylint: disable=import-error,no-name-in-module
    from urllib.parse import quote as url_escape

import pkg_resources

from requests.exceptions import HTTPError as RequestsHTTPError

from custodia import log
from custodia.client import CustodiaSimpleClient


log.warn_provisional(__name__)


main_parser = argparse.ArgumentParser(
    prog='custodia-cli',
    description='Custodia command line interface'
)


def server_check(arg):
    """Check and format --server arg
    """
    if arg.startswith(('http://', 'https://', 'http+unix://')):
        return arg
    if arg.startswith('./'):
        arg = os.path.abspath(arg)
    elif not arg.startswith('/'):
        raise argparse.ArgumentTypeError(
            'Unix socket path must start with / or ./')
    # assume it is a unix socket
    return 'http+unix://{}'.format(url_escape(arg, ''))


def split_header(arg):
    name, value = arg.split('=')
    return name, value


main_parser.add_argument(
    '--server',
    type=server_check,
    default='/var/run/custodia/custodia.sock',
    help=('Custodia server location, supports http://, https://, '
          'or path to a unix socket.')
)
main_parser.add_argument(
    '--uds-urlpath', type=str, default='/secrets/',
    help='URL path for Unix Domain Socket'
)

main_parser.add_argument(
    '--header', type=split_header, action='append',
    help='Extra headers'
)

main_parser.add_argument(
    '--verbose', action='store_true',
)
main_parser.add_argument(
    '--debug', action='store_true',
)

# TLS
main_parser.add_argument(
    '--cafile', type=str, default=None,
    help='PEM encoded file with root CAs'
)
main_parser.add_argument(
    '--certfile', type=str, default=None,
    help='PEM encoded file with certs for TLS client authentication'
)
main_parser.add_argument(
    '--keyfile', type=str, default=None,
    help='PEM encoded key file (if not given, key is read from certfile)'
)


# handlers
def handle_name(args):
    client = args.client_conn
    func = getattr(client, args.command)
    return func(args.name)


def handle_name_value(args):
    client = args.client_conn
    func = getattr(client, args.command)
    return func(args.name, args.value)


# subparsers
subparsers = main_parser.add_subparsers()
subparsers.required = True

parser_create_container = subparsers.add_parser(
    'mkdir',
    help='Create a container')
parser_create_container.add_argument('name', type=str, help='key')
parser_create_container.set_defaults(
    func=handle_name,
    command='create_container')

parser_delete_container = subparsers.add_parser(
    'rmdir',
    help='Delete a container')
parser_delete_container.add_argument('name', type=str, help='key')
parser_delete_container.set_defaults(
    func=handle_name,
    command='delete_container')

parser_list_container = subparsers.add_parser(
    'ls', help='List content of a container')
parser_list_container.add_argument('name', type=str, help='key')
parser_list_container.set_defaults(
    func=handle_name,
    command='list_container')

parser_get_secret = subparsers.add_parser(
    'get', help='Get secret')
parser_get_secret.add_argument('name', type=str, help='key')
parser_get_secret.set_defaults(
    func=handle_name,
    command='get_secret')

parser_set_secret = subparsers.add_parser(
    'set', help='Set secret')
parser_set_secret.add_argument('name', type=str, help='key')
parser_set_secret.add_argument('value', type=str, help='value')
parser_set_secret.set_defaults(
    command='set_secret',
    func=handle_name_value)

parser_del_secret = subparsers.add_parser(
    'del', help='Delete a secret')
parser_del_secret.add_argument('name', type=str, help='key')
parser_del_secret.set_defaults(
    func=handle_name,
    command='del_secret')


# plugins
PLUGINS = [
    'custodia.authenticators', 'custodia.authorizers', 'custodia.clients',
    'custodia.consumers', 'custodia.stores'
]


def handle_plugins(args):
    result = []
    for plugin in PLUGINS:
        result.append('[{}]'.format(plugin))
        eps = sorted(pkg_resources.iter_entry_points(plugin))
        for ep in eps:
            result.append(str(ep))
        result.append('')
    return result[:-1]

parser_plugins = subparsers.add_parser(
    'plugins', help='List plugins')
parser_plugins.set_defaults(
    func=handle_plugins,
    command='plugins')


def main():
    args = main_parser.parse_args()

    if args.debug:
        args.verbose = True
        logdict = logging.Logger.manager.loggerDict
        for obj in logdict.values():
            if not isinstance(obj, logging.Logger):
                continue
            obj.setLevel(logging.DEBUG)

    if args.server.startswith('http+unix://'):
        # append uds-path
        if not args.server.endswith('/'):
            udspath = args.uds_urlpath
            if not udspath.startswith('/'):
                udspath = '/' + udspath
            args.server += udspath

    args.client_conn = CustodiaSimpleClient(args.server)
    if args.header is not None:
        args.client_conn.headers.update(args.header)
    if args.cafile:
        args.client_conn.set_ca_cert(args.cafile)
    if args.certfile:
        args.client_conn.set_client_cert(args.certfile, args.keyfile)
        args.client_conn.headers['CUSTODIA_CERT_AUTH'] = 'true'

    try:
        result = args.func(args)
    except RequestsHTTPError as e:
        return main_parser.exit(1, str(e))
    except Exception as e:  # pylint: disable=broad-except
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        return main_parser.exit(100, str(e))
    if result is not None:
        if isinstance(result, list):
            print('\n'.join(result))
        else:
            print(result)


if __name__ == '__main__':
    main()
