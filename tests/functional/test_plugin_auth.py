# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import pytest

from .base import CustodiaServerWithSimpleCredsAuth, CustodiaTestEnvironment


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

        with CustodiaServerWithSimpleCredsAuth(self.test_dir, meta_uid,
                                               meta_gid) as server:

            container = 'secrets/bucket{}/'.format(self.get_unique_number())

            resp = server.post(container, headers={})
            if expected_access == 'granted':
                assert resp.status_code == 201
            else:
                assert resp.status_code == 403
