# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import os
import subprocess
import time
import unittest

from requests.exceptions import HTTPError

from custodia.client import CustodiaClient


class CustodiaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['PYTHONPATH'] = './'
        pexec = env.get('CUSTODIAPYTHON', 'python')
        try:
            os.unlink('secrets.db')
        except OSError:
            pass
        with (open('testlog.txt', 'a')) as logfile:
            p = subprocess.Popen([pexec, 'custodia/custodia'], env=env,
                                 stdout=logfile, stderr=logfile)
        cls.custodia_process = p
        time.sleep(1)
        cls.client = CustodiaClient('http+unix://%2E%2Fserver_socket/secrets')
        cls.client.headers['REMOTE_USER'] = 'test'
        cls.fwd = CustodiaClient('http+unix://%2E%2Fserver_socket/forwarder')
        cls.fwd.headers['REMOTE_USER'] = 'test'

    @classmethod
    def tearDownClass(cls):
        cls.custodia_process.kill()
        cls.custodia_process.wait()
        try:
            os.unlink('server_socket')
        except OSError:
            pass

    def test_0_create_container(self):
        self.client.create_container('test/container')

    def test_0_delete_container(self):
        self.client.delete_container('test/container')

    def test_1_set_simple_key(self):
        self.client.set_simple_key('test/key', 'VmVycnlTZWNyZXQK')

    def test_2_get_simple_key(self):
        key = self.client.get_simple_key('test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')

    def test_3_list_container(self):
        r = self.client.list_container('test')
        self.assertEqual(r.json(), ["key"])

    def test_4_del_simple_key(self):
        self.client.del_key('test/key')
        try:
            self.client.get_key('test/key')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 404)

    def test_5_list_empty(self):
        r = self.client.list_container('test')
        self.assertEqual(r.json(), [])

    def test_6_create_forwarded_container(self):
        self.fwd.create_container('dir')
        r = self.client.list_container('test/dir')
        self.assertEqual(r.json(), [])

    def test_7_delete_forwarded_container(self):
        self.fwd.delete_container('dir')
        try:
            self.client.list_container('test/dir')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 404)

    def test_8_delete_container(self):
        self.client.delete_container('test')
        try:
            self.client.list_container('test')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 404)

    def test_9_loop(self):
        loop = CustodiaClient('http+unix://%2E%2Fserver_socket/forwarder_loop')
        loop.headers['REMOTE_USER'] = 'test'
        try:
            loop.list_container('test')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 502)
