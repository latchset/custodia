# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import json

from .base import CustodiaServerRunner


class TestKey(CustodiaServerRunner):
    def test_store_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

    def test_store_key_again(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 409

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

    def test_store_key_forbidden_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers={})
        assert resp.status_code == 403

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 404

    def test_store_key_not_valid_container(self, custodia_server):
        bucket_number = self.get_unique_number()
        container = 'secrets/bucket{}/'.format(bucket_number)
        invalid_container = 'secrets/invalid_bucket{}/'.format(bucket_number)
        mykey_with_ivalid_bucket = '{}mykey'.format(invalid_container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey_with_ivalid_bucket,
                                   json={"type": "simple",
                                         "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 404

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

    def test_store_key_directory_instead_of_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey_dir = '{}mykey/'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey_dir, json={"type": "simple",
                                                    "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 405

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

    def test_get_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

        # there need to be application/octet-stream version

    def test_get_key_empty_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 404

        # there need to be application/octet-stream version

    def test_get_key_forbidden_access(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers={})
        assert resp.status_code == 403

        # there need to be application/octet-stream version

    def test_delete_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

        resp = custodia_server.delete(mykey, headers=self.request_headers)
        assert resp.status_code == 204

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 404

    def test_delete_key_empty_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.delete(mykey, headers=self.request_headers)
        assert resp.status_code == 404

    def test_delete_forbidden_access(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'

        resp = custodia_server.delete(mykey, headers={})
        assert resp.status_code == 403

        resp = custodia_server.get(mykey, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'type' in data
        assert data['type'] == 'simple'
        assert 'value' in data
        assert data['value'] == 'P@ssw0rd'
