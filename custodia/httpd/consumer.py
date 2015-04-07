# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.server import HTTPError


DEFAULT_CTYPE = 'text/html; charset=utf-8'
SUPPORTED_COMMANDS = ['GET', 'PUT', 'POST', 'DELETE']


class HTTPConsumer(object):

    def __init__(self, config=None):
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

        if 'Content-type' not in response['headers']:
            response['headers']['Content-type'] = DEFAULT_CTYPE

        if output is not None:
            response['output'] = output

            if 'Content-Length' not in response['headers']:
                if hasattr(output, 'read'):
                    # LOG: warning file-type objects should set Content-Length
                    pass
                else:
                    response['headers']['Content-Length'] = str(len(output))

        return response
