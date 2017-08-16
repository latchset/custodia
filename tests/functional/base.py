# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import grp
import os
import pwd
import shutil
import socket
import subprocess
import sys
import time
from enum import Enum
from string import Template

import pytest

from custodia.client import CustodiaHTTPClient
from custodia.compat import url_escape
from custodia.server.args import parse_args
from custodia.server.config import parse_config


def wait_pid(process, wait):
    timeout = time.time() + wait
    while time.time() < timeout:
        pid, _ = os.waitpid(process.pid, os.WNOHANG)
        if pid == process.pid:
            return True
        time.sleep(0.1)
    return False


def wait_socket(process, custodia_socket, wait):
    timeout = time.time() + wait
    while time.time() < timeout:
        if process.poll() is not None:
            raise AssertionError(
                "Premature termination of Custodia server")
        try:
            s = socket.socket(family=socket.AF_UNIX)
            s.connect(custodia_socket)
        except OSError:
            pass
        else:
            return True
        time.sleep(0.1)
    raise OSError('Timeout error')


def translate_meta_uid(meta_uid):
    current_uid = None

    if meta_uid == "correct_id":
        current_uid = pwd.getpwuid(os.geteuid()).pw_uid

    if meta_uid == "incorrect_id":
        actual_uid = pwd.getpwuid(os.geteuid()).pw_uid
        for uid in [x.pw_uid for x in pwd.getpwall()]:
            if uid != actual_uid:
                current_uid = uid
                break

    if meta_uid == "correct_name":
        current_uid = pwd.getpwuid(os.geteuid()).pw_name

    if meta_uid == "incorrect_name":
        actual_name = pwd.getpwuid(os.geteuid()).pw_name
        for name in [x.pw_name for x in pwd.getpwall()]:
            if name != actual_name:
                current_uid = name
                break

    if meta_uid == "ignore":
        current_uid = -1

    return current_uid


def translate_meta_gid(meta_gid):
    current_gid = None

    if meta_gid == "correct_id":
        current_gid = grp.getgrgid(os.getegid()).gr_gid

    if meta_gid == "incorrect_id":
        actual_user = pwd.getpwuid(os.geteuid()).pw_name
        actual_gid = grp.getgrgid(os.getegid()).gr_gid
        for gid in [g.gr_gid for g in grp.getgrall() if
                    actual_user not in g.gr_mem]:
            if gid != actual_gid:
                current_gid = gid
                break

    if meta_gid == "correct_name":
        current_gid = grp.getgrgid(os.getegid()).gr_name

    if meta_gid == "incorrect_name":
        actual_user = pwd.getpwuid(os.geteuid()).pw_name
        actual_group = grp.getgrgid(os.getegid()).gr_name
        for name in [g.gr_name for g in grp.getgrall() if
                     actual_user not in g.gr_mem]:
            if name != actual_group:
                current_gid = name
                break

    if meta_gid == "ignore":
        current_gid = -1

    return current_gid


class UniqueNumber(object):
    unique_number = 0

    def get_unique_number(self):
        UniqueNumber.unique_number += 1
        return UniqueNumber.unique_number


@pytest.mark.servertest
class CustodiaServerRunner(UniqueNumber):
    request_headers = {'REMOTE_USER': 'me'}
    test_dir = 'tests/functional/tmp'
    custodia_client = None
    env = None
    process = None
    args = None
    config = None
    custodia_conf = None

    @classmethod
    def setup_class(cls):
        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.test_dir)

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

        wait_pid(self.process, 2)
        wait_socket(self.process, self.env['CUSTODIA_SOCKET'], 5)

        arg = '{}/custodia.sock'.format(CustodiaServerRunner.test_dir)
        url = 'http+unix://{}'.format(url_escape(arg, ''))
        self.custodia_client = CustodiaHTTPClient(url)

        def fin():
            self.process.terminate()
            if not wait_pid(self.process, 2):
                self.process.kill()
                if not wait_pid(self.process, 2):
                    raise AssertionError("Hard kill failed")

        request.addfinalizer(fin)
        return self.custodia_client


@pytest.mark.servertest
class CustodiaTestEnvironment(UniqueNumber):
    test_dir = 'tests/functional/tmp_auth_plugin'

    @classmethod
    def setup_class(cls):
        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.test_dir)


class AuthPlugin(Enum):
    SimpleCredsAuth = 1
    SimpleHeaderAuth = 2


class CustodiaServer(object):
    def __init__(self, test_dir, conf_params):
        self.process = None
        self.custodia_client = None
        self.test_dir = test_dir
        self.custodia_conf = os.path.join(self.test_dir, 'custodia.conf')
        self.params = conf_params

        self.out_fd = os.open(os.devnull, os.O_RDWR)

        self._create_configuration()

        self.args = parse_args([self.custodia_conf])
        _, self.config = parse_config(self.args)
        self.env = os.environ.copy()
        self.env['CUSTODIA_SOCKET'] = self.config['server_socket']

    def _get_conf_template(self):
        if self.params['auth_type'] == AuthPlugin.SimpleCredsAuth:
            return 'tests/functional/conf/template_simple_creds_auth.conf'
        if self.params['auth_type'] == AuthPlugin.SimpleHeaderAuth:
            return 'tests/functional/conf/template_simple_header_auth.conf'

    def _create_configuration(self):
        with open(self._get_conf_template()) as f:
            configstr = f.read()

        if self.params['auth_type'] == AuthPlugin.SimpleCredsAuth:
            with (open(self.custodia_conf, 'w+')) as conffile:
                t = Template(configstr)
                conf = t.substitute(
                    {'TEST_DIR': self.test_dir,
                     'UID': translate_meta_uid(self.params['meta_uid']),
                     'GID': translate_meta_gid(self.params['meta_gid'])})
                conffile.write(conf)

        if self.params['auth_type'] == AuthPlugin.SimpleHeaderAuth:
            with (open(self.custodia_conf, 'w+')) as conffile:
                t = Template(configstr)
                conf = t.substitute(
                    {'TEST_DIR': self.test_dir,
                     'HEADER': self.params['header_name'],
                     'VALUE': self.params['header_value']})
                conffile.write(conf)

    def __enter__(self):
        # Don't write server messages to stdout unless we are in debug mode
        # pylint: disable=no-member
        if pytest.config.getoption('debug') or \
                pytest.config.getoption('verbose'):
            stdout = stderr = None
        else:
            stdout = stderr = self.out_fd
        # pylint: enable=no-member

        self.process = subprocess.Popen(
            [sys.executable, '-m', 'custodia.server', self.custodia_conf],
            stdout=stdout, stderr=stderr
        )

        wait_pid(self.process, 2)
        wait_socket(self.process, self.env['CUSTODIA_SOCKET'], 5)

        arg = '{}/custodia.sock'.format(self.test_dir)
        url = 'http+unix://{}'.format(url_escape(arg, ''))
        self.custodia_client = CustodiaHTTPClient(url)

        return self.custodia_client

    def __exit__(self, *args):
        os.remove(self.custodia_conf)
        self.process.terminate()
        if not wait_pid(self.process, 2):
            self.process.kill()
            if not wait_pid(self.process, 2):
                raise AssertionError("Hard kill failed")
        os.close(self.out_fd)
