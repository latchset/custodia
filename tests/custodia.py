# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import
from tests.client import LocalConnection
import os
import subprocess
import time
import unittest


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

    @classmethod
    def AtearDownClass(self):
        os.killpg(self.custodia_process.pid, signal.SIGTERM)

    def test_connect(self):
        conn = LocalConnection('./server_socket')
        conn.connect()
        conn.request('GET', '/', headers={'REMOTE_USER':'tests'})
        r = conn.getresponse()
        self.assertEqual(r.status, 200)
