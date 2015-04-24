# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

try:
    # pylint: disable=import-error
    from httplib import HTTPConnection
except ImportError:
    # pylint: disable=import-error,no-name-in-module
    from http.client import HTTPConnection
import socket


class LocalConnection(HTTPConnection):

    def __init__(self, path):
        HTTPConnection.__init__(self, 'localhost', 0)
        self.unix_socket = path

    def connect(self):
        s = socket.socket(family=socket.AF_UNIX)
        s.connect(self.unix_socket)
        self.sock = s
