# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os


class HTTPAuthorizer(object):

    def __init__(self, config=None):
        self.config = config
        self.store_name = None
        if self.config and 'store' in self.config:
            self.store_name = self.config['store']
        self.store = None

    def handle(self, request):
        raise NotImplementedError


class SimplePathAuthz(HTTPAuthorizer):

    def __init__(self, config=None):
        super(SimplePathAuthz, self).__init__(config)
        self.paths = []
        if 'paths' in self.config:
            self.paths = self.config['paths'].split()

    def handle(self, request):
        path = request.get('path', '')

        # if an authorized path does not end in /
        # check if it matches fullpath for strict match
        for authz in self.paths:
            if authz.endswith('/'):
                continue
            if authz.endswith('.'):
                # special case to match a path ending in /
                authz = authz[:-1]
            if authz == path:
                return True

        while path != '':
            if path in self.paths:
                return True
            if path == '/':
                path = ''
            else:
                path, _ = os.path.split(path)
        return None


class UserNameSpace(HTTPAuthorizer):

    def __init__(self, *args, **kwargs):
        super(UserNameSpace, self).__init__(*args, **kwargs)
        self.path = self.config.get('path', '/')

    def handle(self, request):
        # Only check if we are in the right (sub)path
        path = request.get('path', '/')
        if not path.startswith(self.path):
            return None

        name = request.get('remote_user', None)
        if name is None:
            # UserNameSpace requires a user ...
            return False

        namespace = self.path.rstrip('/') + '/' + name + '/'
        if not path.startswith(namespace):
            # Not in the namespace
            return False

        request['default_namespace'] = name
        return True
