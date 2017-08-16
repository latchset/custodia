# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

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
