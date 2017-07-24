# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import os
import shutil
import socket
import subprocess
import sys
import time
from string import Template

import pytest

from custodia.client import CustodiaHTTPClient
from custodia.compat import url_escape
from custodia.server.args import parse_args
from custodia.server.config import parse_config


@pytest.mark.servertest
class CustodiaServerRunner(object):
    request_headers = {'REMOTE_USER': 'me'}
    test_dir = 'tests/functional/tmp'
    custodia_client = None
    env = None
    process = None
    args = None
    config = None
    custodia_conf = None
    unique_number = 0

    @classmethod
    def setup_class(cls):
        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.test_dir)

    def _wait_pid(self, process, wait):
        timeout = time.time() + wait
        while time.time() < timeout:
            pid, _ = os.waitpid(process.pid, os.WNOHANG)
            if pid == process.pid:
                return True
            time.sleep(0.1)
        return False

    def _wait_socket(self, process, wait):
        timeout = time.time() + wait
        while time.time() < timeout:
            if process.poll() is not None:
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

    def get_unique_number(self):
        CustodiaServerRunner.unique_number = self.unique_number + 1
        return CustodiaServerRunner.unique_number

    @pytest.fixture(scope="class")
    def simple_configuration(self):
        with open('tests/functional/conf/template_simple.conf') as f:
            configstr = f.read()

        self.custodia_conf = os.path.join(self.test_dir, 'custodia.conf')
        with (open(self.custodia_conf, 'w+')) as conffile:
            t = Template(configstr)
            conf = t.substitute({'TEST_DIR': self.test_dir})
            conffile.write(conf)

        self.args = parse_args([self.custodia_conf])
        _, self.config = parse_config(self.args)
        self.env = os.environ.copy()
        self.env['CUSTODIA_SOCKET'] = self.config['server_socket']

    @pytest.fixture(scope="session")
    def dev_null(self, request):
        fd = os.open(os.devnull, os.O_RDWR)

        def close_dev_null():
            os.close(fd)

        request.addfinalizer(close_dev_null)
        return fd

    @pytest.fixture(scope="class")
    def custodia_server(self, simple_configuration, request, dev_null):
        # Don't write server messages to stdout unless we are in debug mode
        # pylint: disable=no-member
        if pytest.config.getoption('debug') or \
                pytest.config.getoption('verbose'):
            stdout = stderr = None
        else:
            stdout = stderr = dev_null
        # pylint: enable=no-member

        self.process = subprocess.Popen(
            [sys.executable, '-m', 'custodia.server', self.custodia_conf],
            stdout=stdout, stderr=stderr
        )

        self._wait_pid(self.process, 2)
        self._wait_socket(self.process, 5)

        arg = '{}/custodia.sock'.format(CustodiaServerRunner.test_dir)
        url = 'http+unix://{}'.format(url_escape(arg, ''))
        self.custodia_client = CustodiaHTTPClient(url)

        def fin():
            self.process.terminate()
            if not self._wait_pid(self.process, 2):
                self.process.kill()
                if not self._wait_pid(self.process, 2):
                    raise AssertionError("Hard kill failed")

        request.addfinalizer(fin)
        return self.custodia_client
