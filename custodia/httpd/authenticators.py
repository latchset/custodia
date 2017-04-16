# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os

from cryptography.hazmat.primitives import constant_time

import requests

from custodia import log
from custodia.plugin import HTTPAuthenticator, PluginOption


class SimpleCredsAuth(HTTPAuthenticator):
    uid = PluginOption('pwd_uid', -1, "User id or name, -1 ignores user")
    gid = PluginOption('grp_gid', -1, "Group id or name, -1 ignores group")

    def handle(self, request):
        creds = request.get('creds')
        if creds is None:
            self.logger.debug('SCA: Missing "creds" from request')
            return False
        uid = int(creds['uid'])
        gid = int(creds['gid'])
        uid_match = self.uid != -1 and self.uid == uid
        gid_match = self.gid != -1 and self.gid == gid
        if uid_match or gid_match:
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
    header = PluginOption(str, 'REMOTE_USER', "header name")
    value = PluginOption('str_set', None,
                         "Comma-separated list of required values")

    def handle(self, request):
        if self.header not in request['headers']:
            self.logger.debug('SHA: No "headers" in request')
            return None
        value = request['headers'][self.header]
        if self.value is not None:
            # pylint: disable=unsupported-membership-test
            if value not in self.value:
                self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], value)
                return False

        self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                              request['client_id'], value)
        request['remote_user'] = value
        return True


class SimpleAuthKeys(HTTPAuthenticator):
    id_header = PluginOption(str, 'CUSTODIA_AUTH_ID', "auth id header name")
    key_header = PluginOption(str, 'CUSTODIA_AUTH_KEY', "auth key header name")
    store = PluginOption('store', None, None)
    store_namespace = PluginOption(str, 'custodiaSAK', "")

    def _db_key(self, name):
        return os.path.join(self.store_namespace, name)

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
                raise ValueError("No such ID")
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
    header = PluginOption(str, 'CUSTODIA_CERT_AUTH', "header name")

    def handle(self, request):
        cert_auth = request['headers'].get(self.header, "false").lower()
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


class OpenIDCTokenAuth(HTTPAuthenticator):
    token_info_url = PluginOption(str, None,
                                  'URL for getting token information')
    client_id = PluginOption(str, None,
                             'Client ID for verifying tokens')
    client_secret = PluginOption(str, None,
                                 'Client Secret for verifying tokens')
    scope = PluginOption(str, 'custodia', 'OAuth2 scope to require')

    def _get_token_info(self, token):
        return requests.post(self.token_info_url,
                             data={'client_id': self.client_id,
                                   'client_secret': self.client_secret,
                                   'token': token,
                                   'token_type_hint': 'Bearer'}).json()

    def handle(self, request):
        token = None
        if 'Authorization' in request['headers']:
            hdr = request['headers']['Authorization']
            if hdr.startswith('Bearer '):
                self.logger.debug('Bearer token provided in header')
                token = hdr[len('Bearer '):]
            else:
                self.logger.debug('Unrecognized Authorization header')
                return False
        elif request.get('access_token'):
            self.logger.debug('Token provided in form')
            token = request.get('access_token')
        else:
            self.logger.debug('Missing any credentials in request')
            return False

        if not token:
            self.logger.debug('No token')
            return False

        try:
            tokeninfo = self._get_token_info(token)
        except:
            self.logger.debug('Error getting token information',
                              exc_info=True)
            return False

        aud = tokeninfo['aud']
        if isinstance(aud, list) and self.client_id not in aud:
            self.logger.debug('My client ID not in audience list')
            return False
        elif self.client_id != aud:
            self.logger.debug('Client ID is not audience')
            return False

        if self.scope not in tokeninfo['scope'].split(' '):
            self.logger.debug('Required scope not found')
            return False

        return True
