# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

from cryptography import x509
from cryptography.hazmat.backends import default_backend

import pytest

from .base import AuthPlugin, CustodiaServer, CustodiaTestEnvironment


class TestBasicsAuthPlugins(CustodiaTestEnvironment):
    @pytest.mark.parametrize("meta_uid,meta_gid,expected_access", [
        ('correct_id', 'correct_id', 'granted'),
        ('correct_id', 'incorrect_id', 'granted'),
        ('correct_id', 'correct_name', 'granted'),
        ('correct_id', 'incorrect_name', 'granted'),
        ('correct_id', 'ignore', 'granted'),
        ('incorrect_id', 'correct_id', 'granted'),
        ('incorrect_id', 'incorrect_id', 'denied'),
        ('incorrect_id', 'correct_name', 'granted'),
        ('incorrect_id', 'incorrect_name', 'denied'),
        ('incorrect_id', 'ignore', 'denied'),
        ('correct_name', 'correct_id', 'granted'),
        ('correct_name', 'incorrect_id', 'granted'),
        ('correct_name', 'correct_name', 'granted'),
        ('correct_name', 'incorrect_name', 'granted'),
        ('correct_name', 'ignore', 'granted'),
        ('incorrect_name', 'correct_id', 'granted'),
        ('incorrect_name', 'incorrect_id', 'denied'),
        ('incorrect_name', 'correct_name', 'granted'),
        ('incorrect_name', 'incorrect_name', 'denied'),
        ('incorrect_name', 'ignore', 'denied'),
        ('ignore', 'correct_id', 'granted'),
        ('ignore', 'incorrect_id', 'denied'),
        ('ignore', 'correct_name', 'granted'),
        ('ignore', 'incorrect_name', 'denied'),
        ('ignore', 'ignore', 'denied'),
    ])
    def test_default_answer_simple_creds_auth(self, meta_uid, meta_gid,
                                              expected_access):

        params = {'auth_type': AuthPlugin.SimpleCredsAuth,
                  'meta_uid': meta_uid,
                  'meta_gid': meta_gid}

        with CustodiaServer(self.test_dir, params) as server:

            container = 'secrets/bucket{}/'.format(self.get_unique_number())

            resp = server.post(container, headers={})
            if expected_access == 'granted':
                assert resp.status_code == 201
            else:
                assert resp.status_code == 403

    # TODO: After https://github.com/latchset/custodia/pull/230
    #       this should be extend by comma-separated cases
    @pytest.mark.parametrize("conf_n,conf_v,call_n,call_v,expected_access", [
        ('REMOTE_USER', 'me', 'REMOTE_USER', 'me', 'granted'),
        ('REMOTE_USER', 'me', 'REMOTE_USER', 'you', 'denied'),
        ('REMOTE_AUTH_USER', 'me', 'REMOTE_AUTH_USER', 'me', 'granted'),
        ('REMOTE_AUTH_USER', 'me', 'REMOTE_USER', 'me', 'denied'),
        ('REMOTE_USER', 'me you he', 'REMOTE_USER', 'me', 'granted'),
        ('REMOTE_USER', 'me you he', 'REMOTE_USER', 'you', 'granted'),
        ('REMOTE_USER', 'me you he', 'REMOTE_USER', 'he', 'granted'),
        ('REMOTE_USER', 'me you he', 'REMOTE_USER', 'she', 'denied'),
    ])
    def test_default_answer_simple_header_auth(self, conf_n, conf_v, call_n,
                                               call_v, expected_access):

        params = {'auth_type': AuthPlugin.SimpleHeaderAuth,
                  'header_name': conf_n,
                  'header_value': conf_v}

        with CustodiaServer(self.test_dir, params) as server:

            container = 'secrets/bucket{}/'.format(self.get_unique_number())

            resp = server.post(container, headers={call_n: call_v})
            if expected_access == 'granted':
                assert resp.status_code == 201
            else:
                assert resp.status_code == 403

    @pytest.mark.parametrize("conf_k,conf_p,call_k,call_p,expected_access", [
        ('qid', 'P@ssw0rd', 'qid', 'P@ssw0rd', 'granted'),
        ('qid', 'P@ssw0rd', 'qid_incorrect', 'P@ssw0rd', 'denied'),
        ('qid', 'P@ssw0rd', 'qid', 'P@ssw0rd_incrorrect', 'denied'),
    ])
    def test_default_answer_simple_auth_keys_auth(self, conf_k, conf_p, call_k,
                                                  call_p, expected_access):

        self.reset_environment()

        # For setup AuthKeys plugin we need authenticate via SimpleHeaderAuth
        params = {'auth_type': AuthPlugin.SimpleHeaderAuth,
                  'header_name': 'REMOTE_USER',
                  'header_value': 'me'}

        with CustodiaServer(self.test_dir, params) as server:
            # Create container
            container = 'secrets/sak/'
            resp = server.post(container, headers={'REMOTE_USER': 'me'})
            assert resp.status_code == 201

            # Save Autheys
            key = '{}{}'.format(container, conf_k)
            resp = server.put(key, json={"type": "simple",
                                         "value": conf_p},
                              headers={'REMOTE_USER': 'me'})
            assert resp.status_code == 201

        # Testing of AuthKeys plugin
        params = {'auth_type': AuthPlugin.SimpleAuthKeys,
                  'store_namespace': 'keys/sak',
                  'store': 'simple'}

        with CustodiaServer(self.test_dir, params) as server:
            container = 'secrets/bucket{}/'.format(self.get_unique_number())

            resp = server.post(container,
                               headers={'CUSTODIA_AUTH_ID': call_k,
                                        'CUSTODIA_AUTH_KEY': call_p})
            if expected_access == 'granted':
                assert resp.status_code == 201
            else:
                assert resp.status_code == 403

    def test_default_answer_simple_client_cert_auth(self):

        params = {'auth_type': AuthPlugin.SimpleClientCert}

        expected_access = True

        with open('tests/ca/custodia-ca.pem', 'rb') as pem_file:
            pem_data = pem_file.read()

        cert = x509.load_pem_x509_certificate(pem_data, default_backend())

        with CustodiaServer(self.test_dir, params) as server:

            container = 'secrets/bucket{}/'.format(self.get_unique_number())

            resp = server.post(container,
                               headers={
                                   'CUSTODIA_CERT_AUTH': str(
                                       cert.public_key())})
            if expected_access == 'granted':
                assert resp.status_code == 201
            else:
                assert resp.status_code == 403
