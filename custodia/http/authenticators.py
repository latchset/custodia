# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.http.server import HTTPError


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
            request['valid_user'] = True
        else:
            raise HTTPError(403)


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
            raise HTTPError(403)
        value = request['headers'][self.name]
        if self.value is None:
            # Any value is accepted
            pass
        elif isinstance(self.value, str):
            if value != self.value:
                raise HTTPError(403)
        elif isinstance(self.value, list):
            if value not in self.value:
                raise HTTPError(403)
        else:
            raise HTTPError(403)

        request['valid_user'] = True
        request['valid_header'] = value
