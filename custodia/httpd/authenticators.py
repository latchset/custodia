# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import grp
import os
import pwd

from cryptography.hazmat.primitives import constant_time

from custodia import log
from custodia.plugin import HTTPAuthenticator


class SimpleCredsAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleCredsAuth, self).__init__(config)
        uid = self.config.get('uid')
        if uid is None:
            self._uid = 0
        else:
            try:
                self._uid = int(uid)
            except ValueError:
                self._uid = pwd.getpwnam(uid).pw_uid

        gid = self.config.get('gid')
        if gid is None:
            self._gid = 0
        else:
            try:
                self._gid = int(gid)
            except ValueError:
                self._gid = grp.getgrnam(gid).gr_gid

    def handle(self, request):
        creds = request.get('creds')
        if creds is None:
            self.logger.debug('SCA: Missing "creds" from request')
            return False
        uid = int(creds['gid'])
        gid = int(creds['uid'])
        if self._gid == gid or self._uid == uid:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'],
                                  "%d, %d" % (uid, gid))
            return True
        else:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'],
                                  "%d, %d" % (uid, gid))
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
            self.logger.debug('SHA: No "headers" in request')
            return None
        value = request['headers'][self.name]
        if self.value is None:
            # Any value is accepted
            pass
        elif isinstance(self.value, str):
            if value != self.value:
                self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], value)
                return False
        elif isinstance(self.value, list):
            if value not in self.value:
                self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], value)
                return False
        else:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'], value)
            return False

        self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                              request['client_id'], value)
        request['remote_user'] = value
        return True


class SimpleAuthKeys(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleAuthKeys, self).__init__(config)
        self.id_header = self.config.get('header', 'CUSTODIA_AUTH_ID')
        self.key_header = self.config.get('header', 'CUSTODIA_AUTH_KEY')
        self.store_name = self.config['store']
        self.store = None
        self.namespace = self.config.get('store_namespace', 'custodiaSAK')

    def _db_key(self, name):
        return os.path.join(self.namespace, name)

    def handle(self, request):
        name = request['headers'].get(self.id_header, None)
        key = request['headers'].get(self.key_header, None)
        if name is None and key is None:
            self.logger.debug('Ignoring request no relevant headers provided')
            return None

        validated = False
        try:
            val = self.store.get(self._db_key(name))
            if val is None:
                raise Exception("No such ID")
            if constant_time.bytes_eq(val.encode('utf-8'),
                                      key.encode('utf-8')):
                validated = True
        except Exception:  # pylint: disable=broad-except
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'], name)
            return False

        if validated:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'], name)
            request['remote_user'] = name
            return True

        self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                              request['client_id'], name)
        return False


class SimpleClientCertAuth(HTTPAuthenticator):
    def __init__(self, config=None):
        super(SimpleClientCertAuth, self).__init__(config)
        self.id_header = self.config.get('header', 'CUSTODIA_CERT_AUTH')

    def handle(self, request):
        cert_auth = request['headers'].get(self.id_header, "false").lower()
        client_cert = request['client_cert']  # {} or None
        if not client_cert or cert_auth not in {'1', 'yes', 'true', 'on'}:
            self.logger.debug('Ignoring request no relevant header or cert'
                              ' provided')
            return None

        subject = client_cert.get('subject', {})
        dn = []
        name = None
        # TODO: check SAN first
        for rdn in subject:
            for key, value in rdn:
                dn.append('{}="{}"'.format(key, value.replace('"', r'\"')))
                if key == 'commonName':
                    name = value
                    break

        dn = ', '.join(dn)
        self.logger.debug('Client cert subject: {}, serial: {}'.format(
            dn, client_cert.get('serialNumber')))

        if name:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'], name)
            request['remote_user'] = name
            return True

        self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                              request['client_id'], dn)
        return False
