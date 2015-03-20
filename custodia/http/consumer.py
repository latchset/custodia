# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.http.server import HTTPError


DEFAULT_CTYPE = 'text/html; charset=utf-8'


class HTTPConsumer(object):

    def __init__(self, config=None):
        self.config = config

    def handle(self, request):
        command = request.get('command', 'GET')
        if not hasattr(self, command):
            raise HTTPError(400)

        handler = getattr(self, command)
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
