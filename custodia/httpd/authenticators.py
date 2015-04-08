# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.server import HTTPError
import os


class HTTPAuthenticator(object):

    def __init__(self, config=None):
        self.config = config

    def handle(self, request):
        raise HTTPError(403)


class SimpleCredsAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleCredsAuth, self).__init__(config)
        self._uid = 0
        self._gid = 0
        if 'uid' in self.config:
            self._uid = int(self.config['uid'])
        if 'gid' in self.config:
            self._gid = int(self.config['gid'])

    def handle(self, request):
        uid = int(request['creds']['gid'])
        gid = int(request['creds']['uid'])
        if self._gid == gid or self._uid == uid:
            return True
        else:
            return False


class SimpleHeaderAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleHeaderAuth, self).__init__(config)
        self.name = 'REMOTE_USER'
        self.value = None
        if 'header' in self.config:
            self.name = self.config['header']
        if 'value' in self.config:
            self.value = self.config['value']

    def handle(self, request):
        if self.name not in request['headers']:
            return False
        value = request['headers'][self.name]
        if self.value is None:
            # Any value is accepted
            pass
        elif isinstance(self.value, str):
            if value != self.value:
                return False
        elif isinstance(self.value, list):
            if value not in self.value:
                return False
        else:
            return False

        request['remote_user'] = value
        return True


class SimpleNULLAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleNULLAuth, self).__init__(config)
        self.paths = []
        if 'paths' in self.config:
            self.paths = self.config['paths'].split()

    def handle(self, request):
        path = request.get('path', '')
        while path != '':
            if path in self.paths:
                return True
            if path == '/':
                path = ''
            else:
                path, _ = os.path.split(path)
        return None
