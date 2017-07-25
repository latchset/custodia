#!/usr/bin/env python
import os
import shutil
import socket
import subprocess
import sys
import time
import unittest
from string import Template

import requests

from custodia.client import HTTPUnixAdapter
from custodia.server.args import parse_args
from custodia.server.config import parse_config


class CustodiaServerBase(unittest.TestCase):
    """ Basic class for a Custodia Server

    Setup an Custodia server based in a Custodia conf file.
    In addition, create an wrapper for the API calls.
    """

    request_headers = {'REMOTE_USER': 'me'}
    test_dir = 'tests/functional/tmp'

    def setUp(self):
        super(CustodiaServerBase, self).setUp()

    def create_server(self, configfile=None, configstr=None):
        """Create a Custodia server based in a custodia configuration
        file.

        :param configfile: Custodia config file
        :param configstr: string variable with the configuration info
        '''
        """
        if configfile is not None and configstr is not None:
            raise ValueError
        if configfile is not None:
            with open(configfile) as f:
                configstr = f.read()

        if os.path.isdir(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.configstr = configstr
        custodia_conf = os.path.join(self.test_dir, 'custodia.conf')
        with (open(custodia_conf, 'w+')) as conffile:
            t = Template(self.configstr)
            conf = t.substitute({'TEST_DIR': self.test_dir})
            conffile.write(conf)
        self.args = parse_args([custodia_conf])
        self.parser, self.config = parse_config(self.args)
        self.env = os.environ.copy()
        self.env['CUSTODIA_TMPDIR'] = self.test_dir
        self.env['CUSTODIA_SOCKET'] = self.config['server_socket']
        self.process = subprocess.Popen(
            [sys.executable, '-m', 'custodia.server', custodia_conf]
        )
        self._wait_pid(self.process, 2)
        self._wait_socket(self.process, 5)
        self.session = requests.Session()
        self.session.mount('http+unix://', HTTPUnixAdapter())

    def tearDown(self):
        self.process.terminate()
        if not self._wait_pid(self.process, 2):
            self.process.kill()
            if not self._wait_pid(self.process, 2):
                raise AssertionError("Hard kill failed")
        shutil.rmtree(self.test_dir)

    def _wait_pid(self, process, wait):
        timeout = time.time() + wait
        while time.time() < timeout:
            pid, status = os.waitpid(process.pid, os.WNOHANG)
            if pid == process.pid:
                return True
            time.sleep(0.1)
        return False

    def _wait_socket(self, process, wait):
        timeout = time.time() + wait
        while time.time() < timeout:
            if self.process.poll() is not None:
                raise AssertionError(
                    "Premature termination of Custodia server")
            try:
                s = socket.socket(family=socket.AF_UNIX)
                s.connect(self.env['CUSTODIA_SOCKET'])
            except OSError:
                pass
            else:
                return True
            time.sleep(0.1)
        raise OSError('Timeout error')

    def GET(self, path, **kwargs):
        return self.session.get(path, headers=self.request_headers)

    def PUT(self, path, key):
        self.request_headers['Content-Type'] = 'application/octet-stream'
        return self.session.put(path, header=self.request_headers, json=key)

    def POST(self, path):
        return self.session.post(path, headers=self.request_headers)

    def DELETE(self, path):
        return self.session.delete(path, headers=self.request_headers)
