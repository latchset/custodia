# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

import collections
import json

from custodia.client import CustodiaSimpleClient
from custodia.compat import configparser

from requests.exceptions import HTTPError


class CustodiaSectionProxy(configparser.SectionProxy):
    """A section proxy that supports getsecret()
    """
    def getsecret(self, option, fallback=None, **kwargs):
        # keyword-only arguments
        raw = kwargs.get('raw', False)
        var = kwargs.get('vars', None)

        return self._parser.getsecret(self._name, option, raw=raw,
                                      vars=var, fallback=fallback)


class CustodiaMapping(collections.Mapping):
    """Custodia client proxy

    The class provides a read-only mapping interface that forwards item
    lookup to a Custodia client. It is used to implement
    ${CUSTODIA:some/key} interpolation where CUSTODIA is an instance of this
    class and 'some/key' is requested from a Custodia server.
    """
    __slots__ = ('_parser', )

    def __init__(self, parser):
        self._parser = parser

    def __getitem__(self, item):
        return self._parser.custodia_client.get_secret(item)

    def __len__(self):
        # don't bother to get len or iter from remote
        return 0

    def __iter__(self):
        return {}.__iter__()


class CustodiaConfigParser(configparser.ConfigParser):
    """Python 3 like config parser with Custodia support.

    Example config::

        [custodia_client]
        url = https://custodia.example/secrets
        [example]
        password = test/key
        [interpolation]
        password = ${CUSTODIA:test/key}

    parser = CustodiaConfigParser()
    secret = parser.getsecret('example', 'password')
    secret = parser.get('interpolation', 'password')

    The Custodia client instance can either be passed to CustodiaConfigParser
    or loaded from the [custodia_client] section.

    """
    _DEFAULT_INTERPOLATION = configparser.ExtendedInterpolation()
    custodia_client_section = 'custodia_client'
    custodia_section = 'CUSTODIA'

    def __init__(self, defaults=None, dict_type=collections.OrderedDict,
                 allow_no_value=False, custodia_client=None, **kwargs):
        super(CustodiaConfigParser, self).__init__(
            defaults=defaults, dict_type=dict_type,
            allow_no_value=allow_no_value, **kwargs)
        self._sections[self.custodia_section] = CustodiaMapping(self)
        self._custodia_client = custodia_client

    def __getitem__(self, key):
        item = super(CustodiaConfigParser, self).__getitem__(key)
        # wrap SectionProxy in CustodiaSectionProxy
        if not isinstance(item, CustodiaSectionProxy):
            item = CustodiaSectionProxy(item.parser, item.name)
            self._proxies[key] = item
        return item

    @property
    def custodia_client(self):
        if self._custodia_client is None:
            sec = self.custodia_client_section
            url = self.get(sec, 'url')
            client = CustodiaSimpleClient(url)
            headers = self.get(sec, 'headers', fallback=None)
            if headers:
                headers = json.loads(headers)
                client.headers.update(headers)
            tls_cafile = self.get(sec, 'tls_cafile', fallback=None)
            if tls_cafile:
                client.set_ca_cert(tls_cafile)
            certfile = self.get(sec, 'tls_certfile', fallback=None)
            keyfile = self.get(sec, 'tls_keyfile', fallback=None)
            if certfile:
                client.set_client_cert(certfile, keyfile)
            self._custodia_client = client

        return self._custodia_client

    def getsecret(self, section, option, **kwargs):
        """Get a secret from Custodia
        """
        # keyword-only arguments, vars and fallback are directly passed through
        raw = kwargs.get('raw', False)
        value = self.get(section, option, **kwargs)
        if raw:
            return value
        return self.custodia_client.get_secret(value)


def demo():
    import textwrap
    cfg = textwrap.dedent(u"""
        [custodia_client]
        url = http+unix://%2E%2Fserver_socket/secrets
        headers = {"REMOTE_USER": "user"}

        [example]
        password = test/key

        [interpolation]
        password = ${CUSTODIA:test/key}
    """)
    parser = CustodiaConfigParser()
    parser.read_string(cfg)

    # create entries
    try:
        c = parser.custodia_client.list_container('test')
    except HTTPError:
        parser.custodia_client.create_container('test')
        c = []
    if 'key' not in c:
        parser.custodia_client.set_secret('test/key', 'secret password')

    # get entries from Custodia
    secret = parser.getsecret('example', 'password')
    print(secret)
    secret = parser.get('interpolation', 'password')
    print(secret)

if __name__ == '__main__':
    demo()
