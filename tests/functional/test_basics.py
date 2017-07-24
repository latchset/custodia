# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import json

from .base import CustodiaServerRunner


class TestBasics(CustodiaServerRunner):
    def test_default_answer(self, custodia_server):
        resp = custodia_server.get('http://localhost/',
                                   headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'message' in data
        assert data['message'] == 'Quis custodiet ipsos custodes?'

    def test_server_string(self, custodia_server):
        resp = custodia_server.get('http://localhost/',
                                   headers=self.request_headers)
        assert resp.status_code == 200
        assert 'Server' in resp.headers
        assert resp.headers['Server'] == 'Test_Custodia_Server'
        data = json.loads(resp.text)
        assert 'message' in data
        assert data['message'] == 'Quis custodiet ipsos custodes?'

    def test_raw_data_method(self, custodia_server):
        resp = custodia_server.post('secrets/bucket/',
                                    headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put('secrets/bucket/mykey',
                                   json={"type": "simple",
                                         "value": 'P@ssw0rd'},
                                   headers={'Content-Type':
                                            'application/octet-stream',
                                            'REMOTE_USER': 'me'})
        assert resp.status_code == 201

        resp = custodia_server.get('secrets/bucket/mykey', headers={
            'Content-Type': 'application/octet-stream', 'REMOTE_USER': 'me'})
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'
