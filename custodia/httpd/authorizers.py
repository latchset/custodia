# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os

from custodia import log
from custodia.plugin import HTTPAuthorizer


class SimplePathAuthz(HTTPAuthorizer):

    def __init__(self, config=None):
        super(SimplePathAuthz, self).__init__(config)
        self.paths = []
        if 'paths' in self.config:
            self.paths = self.config['paths'].split()

    def handle(self, request):
        reqpath = path = request.get('path', '')

        # if an authorized path does not end in /
        # check if it matches fullpath for strict match
        for authz in self.paths:
            if authz.endswith('/'):
                continue
            if authz.endswith('.'):
                # special case to match a path ending in /
                authz = authz[:-1]
            if authz == path:
                self.audit_svc_access(log.AUDIT_SVC_AUTHZ_PASS,
                                      request['client_id'], path)
                return True

        while path != '':
            if path in self.paths:
                self.audit_svc_access(log.AUDIT_SVC_AUTHZ_PASS,
                                      request['client_id'], path)
                return True
            if path == '/':
                path = ''
            else:
                path, _ = os.path.split(path)

        self.logger.debug('No path in %s matched %s', self.paths, reqpath)
        return None


class UserNameSpace(HTTPAuthorizer):

    def __init__(self, *args, **kwargs):
        super(UserNameSpace, self).__init__(*args, **kwargs)
        self.path = self.config.get('path', '/')

    def handle(self, request):
        # Only check if we are in the right (sub)path
        path = request.get('path', '/')
        if not path.startswith(self.path):
            self.logger.debug('%s is not contained in %s', path, self.path)
            return None

        name = request.get('remote_user', None)
        if name is None:
            # UserNameSpace requires a user ...
            self.audit_svc_access(log.AUDIT_SVC_AUTHZ_FAIL,
                                  request['client_id'], path)
            return False

        namespace = self.path.rstrip('/') + '/' + name + '/'
        if not path.startswith(namespace):
            # Not in the namespace
            self.audit_svc_access(log.AUDIT_SVC_AUTHZ_FAIL,
                                  request['client_id'], path)
            return False

        request['default_namespace'] = name
        self.audit_svc_access(log.AUDIT_SVC_AUTHZ_PASS,
                              request['client_id'], path)
        return True
