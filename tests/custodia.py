# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import json
import os
import subprocess
import time
import unittest

from tests.client import LocalConnection


class CustodiaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['PYTHONPATH'] = './'
        pexec = env.get('CUSTODIAPYTHON', 'python')
        devnull = open(os.devnull, "w")
        p = subprocess.Popen([pexec, 'custodia/custodia'], env=env,
                             stdout=devnull, stderr=devnull)
        cls.custodia_process = p
        time.sleep(1)
        cls.dfl_headers = {'REMOTE_USER': 'test',
                           'Content-Type': 'application/json'}

    @classmethod
    def tearDownClass(cls):
        cls.custodia_process.kill()
        cls.custodia_process.wait()
        for fname in ['server_socket', 'secrets.db']:
            try:
                os.unlink(fname)
            except OSError:
                pass

    def _make_request(self, cmd, path, headers=None, body=None):
        conn = LocalConnection('./server_socket')
        conn.connect()
        conn.request(cmd, path, body=body, headers=self.dfl_headers)
        return conn.getresponse()

    def test_connect(self):
        r = self._make_request('GET', '/', {'REMOTE_USER': 'tests'})
        self.assertEqual(r.status, 200)

    def test_simple_0_set_key(self):
        data = {'type': 'simple', 'value': 'VmVycnlTZWNyZXQK'}
        r = self._make_request('PUT', '/secrets/test/key',
                               self.dfl_headers, json.dumps(data))
        self.assertEqual(r.status, 201)

    def test_simple_1_get_key(self):
        r = self._make_request('GET', '/secrets/test/key', self.dfl_headers)
        self.assertEqual(r.status, 200)
        body = r.read().decode('utf-8')
        data = {'type': 'simple', 'value': 'VmVycnlTZWNyZXQK'}
        self.assertEqual(json.loads(body), data)

    def test_simple_2_del_key(self):
        r = self._make_request('DELETE', '/secrets/test/key', self.dfl_headers)
        self.assertEqual(r.status, 204)
