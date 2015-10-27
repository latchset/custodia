# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import socket

import requests

from requests.adapters import HTTPAdapter
from requests.compat import unquote, urlparse

from requests.packages.urllib3.connection import HTTPConnection
from requests.packages.urllib3.connectionpool import HTTPConnectionPool


class HTTPUnixConnection(HTTPConnection):

    def __init__(self, host, timeout=60, **kwargs):
        super(HTTPConnection, self).__init__('localhost')
        self.unix_socket = host
        self.timeout = timeout

    def connect(self):
        s = socket.socket(family=socket.AF_UNIX)
        s.settimeout(self.timeout)
        s.connect(self.unix_socket)
        self.sock = s


class HTTPUnixConnectionPool(HTTPConnectionPool):

    scheme = 'http+unix'
    ConnectionCls = HTTPUnixConnection


class HTTPUnixAdapter(HTTPAdapter):

    def get_connection(self, url, proxies=None):
        # proxies, silently ignored
        path = unquote(urlparse(url).netloc)
        return HTTPUnixConnectionPool(path)


DEFAULT_HEADERS = {'Content-Type': 'application/json'}


class CustodiaHTTPClient(object):

    def __init__(self, url):
        self.session = requests.Session()
        self.session.mount('http+unix://', HTTPUnixAdapter())
        self.headers = dict(DEFAULT_HEADERS)
        self.url = url
        self._last_response = None

    def set_simple_auth_keys(self, name, key,
                             name_header='CUSTODIA_AUTH_ID',
                             key_header='CUSTODIA_AUTH_KEY'):
        self.headers[name_header] = name
        self.headers[key_header] = key

    def _join_url(self, path):
        return self.url.rstrip('/') + '/' + path.lstrip('/')

    def _add_headers(self, **kwargs):
        headers = kwargs.get('headers', None)
        if headers is None:
            headers = dict()
        headers.update(self.headers)
        return headers

    def _request(self, cmd, path, **kwargs):
        self._last_response = None
        url = self._join_url(path)
        kwargs['headers'] = self._add_headers(**kwargs)
        self._last_response = cmd(url, **kwargs)
        return self._last_response

    @property
    def last_response(self):
        return self._last_response

    def delete(self, path, **kwargs):
        return self._request(self.session.delete, path, **kwargs)

    def get(self, path, **kwargs):
        return self._request(self.session.get, path, **kwargs)

    def head(self, path, **kwargs):
        return self._request(self.session.head, path, **kwargs)

    def patch(self, path, **kwargs):
        return self._request(self.session.patch, path, **kwargs)

    def post(self, path, **kwargs):
        return self._request(self.session.post, path, **kwargs)

    def put(self, path, **kwargs):
        return self._request(self.session.put, path, **kwargs)

    def container_name(self, name):
        return name if name.endswith('/') else name + '/'

    def create_container(self, name):
        raise NotImplementedError

    def list_container(self, name):
        raise NotImplementedError

    def delete_container(self, name):
        raise NotImplementedError

    def get_secret(self, name):
        raise NotImplementedError

    def set_secret(self, name, value):
        raise NotImplementedError

    def del_secret(self, name):
        raise NotImplementedError


class CustodiaSimpleClient(CustodiaHTTPClient):

    def create_container(self, name):
        r = self.post(self.container_name(name))
        r.raise_for_status()

    def delete_container(self, name):
        r = self.delete(self.container_name(name))
        r.raise_for_status()

    def list_container(self, name):
        r = self.get(self.container_name(name))
        r.raise_for_status()
        return r.json()

    def get_secret(self, name):
        r = self.get(name)
        r.raise_for_status()
        simple = r.json()
        ktype = simple.get("type", None)
        if ktype != "simple":
            raise TypeError("Invalid key type: %s" % ktype)
        return simple["value"]

    def set_secret(self, name, value):
        r = self.put(name, json={"type": "simple", "value": value})
        r.raise_for_status()

    def del_secret(self, name):
        r = self.delete(name)
        r.raise_for_status()
