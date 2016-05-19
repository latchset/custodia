# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from jwcrypto.common import json_encode

import six

from custodia.httpd.server import HTTPError
from custodia.log import CustodiaPlugin


DEFAULT_CTYPE = 'text/html; charset=utf-8'
SUPPORTED_COMMANDS = ['GET', 'PUT', 'POST', 'DELETE']


class HTTPConsumer(CustodiaPlugin):

    def __init__(self, config=None):
        super(HTTPConsumer, self).__init__(config)
        self.config = config
        self.store_name = None
        if config and 'store' in config:
            self.store_name = config['store']
        self.store = None
        self.subs = dict()
        self.root = self

    def add_sub(self, name, sub):
        self.subs[name] = sub
        if hasattr(sub, 'root'):
            sub.root = self.root

    def _find_handler(self, request):
        base = self
        command = request.get('command', 'GET')
        if command not in SUPPORTED_COMMANDS:
            raise HTTPError(501)
        trail = request.get('trail', None)
        if trail is not None:
            for comp in trail:
                subs = getattr(base, 'subs', {})
                if comp in subs:
                    base = subs[comp]
                    trail.pop(0)
                else:
                    break

        handler = getattr(base, command)
        if handler is None:
            raise HTTPError(400)

        return handler

    def handle(self, request):
        handler = self._find_handler(request)
        response = {'headers': dict()}

        # Handle request
        output = handler(request, response)
        if output is None:
            output = response.get('output')

        ct = response['headers'].get('Content-Type')
        if ct is None:
            ct = response['headers']['Content-Type'] = DEFAULT_CTYPE

        if 'application/json' in ct and isinstance(output, (dict, list)):
            output = json_encode(output).encode('utf-8')
            response['headers']['Content-Length'] = str(len(output))

        response['output'] = output

        if output is not None and not hasattr(output, 'read') \
                and not isinstance(output, six.binary_type):
            msg = "Handler {} returned unsupported type {} ({}):\n{!r}"
            raise TypeError(msg.format(handler, type(output), ct, output))

        if output is not None and 'Content-Length' not in response['headers']:
            if hasattr(output, 'read'):
                # LOG: warning file-type objects should set Content-Length
                pass
            else:
                response['headers']['Content-Length'] = str(len(output))

        return response
