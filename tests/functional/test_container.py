# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import json

from .base import CustodiaServerRunner


class TestContainer(CustodiaServerRunner):
    def test_create_container(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

    def test_create_container_again(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 200

    def test_create_container_invalid_format(self, custodia_server):
        invalid_container = 'secrets/bucket{}'.format(self.get_unique_number())

        resp = custodia_server.post(invalid_container,
                                    headers=self.request_headers)
        assert resp.status_code == 405

    def test_create_container_forbidden_key(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())

        resp = custodia_server.post(container, headers={})
        assert resp.status_code == 403

    def test_list_container(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())
        mykey = '{}mykey'.format(container)
        yourkey = '{}yourkey'.format(container)

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.put(mykey, json={"type": "simple",
                                                "value": 'P@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

        resp = custodia_server.put(yourkey, json={"type": "simple",
                                                  "value": 'AnotherP@ssw0rd'},
                                   headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data
        assert 'yourkey' in data

    def test_remove_container(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.delete(container, headers=self.request_headers)
        assert resp.status_code == 204

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 404

    def test_remove_container_not_empty(self, custodia_server):
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

        resp = custodia_server.delete(container, headers=self.request_headers)
        assert resp.status_code == 409

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data

    def test_remove_container_not_found(self, custodia_server):
        container = 'secrets/bucket{}/'.format(self.get_unique_number())

        resp = custodia_server.post(container, headers=self.request_headers)
        assert resp.status_code == 201

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        assert resp.text == '[]'

        resp = custodia_server.delete(container, headers=self.request_headers)
        assert resp.status_code == 204

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 404

        resp = custodia_server.delete(container, headers=self.request_headers)
        assert resp.status_code == 404

    def test_remove_container_forbidden_key(self, custodia_server):
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

        resp = custodia_server.delete(container, headers={})
        assert resp.status_code == 403

        resp = custodia_server.get(container, headers=self.request_headers)
        assert resp.status_code == 200
        data = json.loads(resp.text)
        assert 'mykey' in data
