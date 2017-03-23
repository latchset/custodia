# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import os
import shutil
import socket
import subprocess
import sys
import time
import unittest
from string import Template

from jwcrypto import jwk

import pytest

from requests.exceptions import HTTPError, SSLError

import six

from custodia.client import CustodiaKEMClient, CustodiaSimpleClient
from custodia.compat import configparser, quote_plus
from custodia.store.sqlite import SqliteStore


# mark all tests in this module as 'servertest' test cases
pytestmark = pytest.mark.servertest


def find_port(host='localhost'):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


TEST_CUSTODIA_CONF = u"""
[global]
server_version = "Secret/0.0.7"
server_url = ${SOCKET_URL}
auditlog = ${TEST_DIR}/test_audit.log
debug = True
tls_certfile = tests/ca/custodia-server.pem
tls_keyfile = tests/ca/custodia-server.key
tls_cafile = tests/ca/custodia-ca.pem
tls_verify_client = ${VERIFY_CLIENT}
umask = 027

[auth:header]
handler = SimpleHeaderAuth
header = REMOTE_USER

[auth:clientcert]
handler = SimpleClientCertAuth

[authz:paths]
handler = custodia.httpd.authorizers.SimplePathAuthz
paths = /. /secrets

[authz:namespaces]
handler = custodia.httpd.authorizers.UserNameSpace
path = /secrets/uns
store = simple

[store:simple]
handler = custodia.store.sqlite.SqliteStore
dburi = ${TEST_DIR}/test_secrets.db
table = secrets
filemode = 640

[/]
handler = Root

[/secrets]
handler = custodia.secrets.Secrets
store = simple

[/secrets/uns]
handler = custodia.secrets.Secrets
store = simple

# Forward
[auth:forwarder]
handler = custodia.httpd.authenticators.SimpleAuthKeys
store_namespace = keys/sak
store = simple

[authz:forwarders]
handler = custodia.httpd.authorizers.SimplePathAuthz
paths = /forwarder /forwarder_loop

[/forwarder]
handler = Forwarder
prefix_remote_user = False
forward_uri = ${SOCKET_URL}/secrets/fwd
tls_certfile = tests/ca/custodia-client.pem
tls_keyfile = tests/ca/custodia-client.key
tls_cafile = tests/ca/custodia-ca.pem
forward_headers = {"CUSTODIA_AUTH_ID": "${TEST_AUTH_ID}", \
    "CUSTODIA_AUTH_KEY": "${TEST_AUTH_KEY}"}

[/forwarder_loop]
handler = custodia.forwarder.Forwarder
forward_uri = ${SOCKET_URL}/forwarder_loop
tls_certfile = tests/ca/custodia-client.pem
tls_keyfile = tests/ca/custodia-client.key
tls_cafile = tests/ca/custodia-ca.pem
forward_headers = {"REMOTE_USER": "test"}


# Encgen
[store:encgen]
handler = custodia.store.encgen.EncryptedOverlay
backing_store = simple
master_key = ${TEST_DIR}/test_mkey.conf
master_enctype = A128CBC-HS256

[authz:enc]
handler = SimplePathAuthz
paths = /enc

[authz:enc_kem]
handler = KEMKeysStore
server_keys = srvkid
store = simple
paths = /enc/kem

[/enc]
handler = Secrets
allowed_keytypes = simple kem
store = encgen
"""


TEST_SOCKET_URL = "http+unix://%2E%2Ftests%2Ftmp%2Ftest_socket"


def generate_all_keys(custodia_conf):
    parser = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation()
    )
    with open(custodia_conf) as f:
        parser.read_file(f)

    filename = parser.get('store:encgen', 'master_key')
    key = jwk.JWK(generate='oct', size=256)
    with open(filename, 'w+') as keyfile:
        keyfile.write(key.export())

    store = SqliteStore(parser, 'store:simple')

    srv_kid = "srvkid"
    cli_kid = "clikid"
    ss_key = jwk.JWK(generate='RSA', kid=srv_kid, use="sig")
    se_key = jwk.JWK(generate='RSA', kid=srv_kid, use="enc")
    store.set('kemkeys/sig/%s' % srv_kid, ss_key.export())
    store.set('kemkeys/enc/%s' % srv_kid, se_key.export())

    cs_key = jwk.JWK(generate='RSA', kid=cli_kid, use="sig")
    ce_key = jwk.JWK(generate='RSA', kid=cli_kid, use="enc")
    store.set('kemkeys/sig/%s' % cli_kid, cs_key.export_public())
    store.set('kemkeys/enc/%s' % cli_kid, ce_key.export_public())
    return ([ss_key.export_public(), se_key.export_public()],
            [cs_key.export(), ce_key.export()])


class CustodiaTests(unittest.TestCase):
    socket_url = TEST_SOCKET_URL
    test_auth_id = "test_user"
    test_auth_key = "cd54b735-e756-4f12-aa18-d85509baef36"
    verify_client = 'False'
    test_dir = 'tests/tmp'

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['PYTHONPATH'] = './'
        cls.pexec = env.get('CUSTODIAPYTHON', sys.executable)

        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir)

        custodia_conf = os.path.join(cls.test_dir, 'test_custodia.conf')
        with (open(custodia_conf, 'w+')) as conffile:
            t = Template(TEST_CUSTODIA_CONF)
            conf = t.substitute({'SOCKET_URL': cls.socket_url,
                                 'TEST_DIR': cls.test_dir,
                                 'TEST_AUTH_ID': cls.test_auth_id,
                                 'TEST_AUTH_KEY': cls.test_auth_key,
                                 'VERIFY_CLIENT': cls.verify_client})
            conffile.write(conf)

        srvkeys, clikeys = generate_all_keys(custodia_conf)

        test_log_file = os.path.join(cls.test_dir, 'test_log.txt')
        with (open(test_log_file, 'a')) as logfile:
            p = subprocess.Popen(
                [cls.pexec, '-m', 'custodia.server', custodia_conf],
                env=env, stdout=logfile, stderr=logfile
            )
        time.sleep(1)
        if p.poll() is not None:
            raise AssertionError(
                "Premature termination of Custodia server, see test_log.txt")
        cls.custodia_process = p

        cls.client = cls.create_client('/secrets/uns', 'test')
        cls.admin = cls.create_client('/secrets', 'admin')
        cls.fwd = cls.create_client('/forwarder', 'test')
        cls.loop = cls.create_client('/forwarder_loop', 'test')
        cls.enc = cls.create_client('/enc', 'enc')
        cls.root = cls.create_client('/', 'test')

        cls.kem = cls.create_client('/enc', 'kem', CustodiaKEMClient)
        cls.kem.set_server_public_keys(*srvkeys)
        cls.kem.set_client_keys(*clikeys)
        cls.custodia_cli_args = [
            cls.pexec,
            '-Wignore',
            '-m', 'custodia.cli',
            '--debug',
            '--header', 'REMOTE_USER=test',
            '--server', cls.socket_url
        ]

    @classmethod
    def create_client(cls, suffix, remote_user, clientcls=None):
        if clientcls is None:
            clientcls = CustodiaSimpleClient
        client = clientcls(cls.socket_url + suffix)
        if remote_user:
            client.headers['REMOTE_USER'] = remote_user
        return client

    @classmethod
    def tearDownClass(cls):
        cls.custodia_process.kill()
        cls.custodia_process.wait()

    def _custoda_cli(self, *extra_args, **kwargs):
        args = list(self.custodia_cli_args)
        args.extend(extra_args)
        try:
            out = subprocess.check_output(args, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                # HTTP error, reraise
                raise
            else:
                # other other
                out = e.output
                if not isinstance(out, six.text_type):
                    out = out.decode('utf-8')
                self.fail(out)

        if not isinstance(out, six.text_type):
            out = out.decode('utf-8')
        # remove trailing new line
        out = out.rstrip()
        if kwargs.get('split'):
            out = out.split('\n')
        return out

    def test_0_0_setup(self):
        self.admin.create_container('fwd')
        self.admin.create_container('sak')
        self.admin.set_secret('sak/' + self.test_auth_id, self.test_auth_key)
        self.admin.create_container('test')

    def test_0_create_container(self):
        self.client.create_container('test/container')

    def test_0_delete_container(self):
        self.client.delete_container('test/container')

    def test_0_get_root(self):
        r = self.root.get('')
        r.raise_for_status()
        msg = r.json()
        self.assertEqual(msg, {"message": "Quis custodiet ipsos custodes?"})

    def test_1_set_simple_key(self):
        self.client.set_secret('test/key', 'VmVycnlTZWNyZXQK')
        urlkey = 'test/{}'.format(quote_plus('http://localhost:5000'))
        self.client.set_secret(urlkey, 'path with /')

    def test_1_set_simple_key_cli(self):
        self._custoda_cli('set', 'test/cli', 'oaxaif4poo0Waec')

    def test_2_get_simple_key(self):
        key = self.client.get_secret('test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')
        key = self.client.get_secret('test/http%3A%2F%2Flocalhost%3A5000')
        self.assertEqual(key, 'path with /')

    def test_2_get_simple_key_cli(self):
        key = self._custoda_cli('get', 'test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')
        key = self._custoda_cli('get', 'test/cli')
        self.assertEqual(key, 'oaxaif4poo0Waec')

    def test_3_list_container(self):
        cl = self.client.list_container('test')
        self.assertEqual(cl, ["cli", "http://localhost:5000", "key"])

    def test_3_list_container_cli(self):
        cl = self._custoda_cli('ls', 'test', split=True)
        self.assertEqual(cl, ["cli", "http://localhost:5000", "key"])

    def test_4_del_simple_key(self):
        self.client.del_secret('test/key')
        self.client.del_secret('test/http%3A%2F%2Flocalhost%3A5000')
        try:
            self.client.get_secret('test/key')
        except HTTPError:
            self.assertEqual(self.client.last_response.status_code, 404)
        try:
            self.client.get_secret('test/http%3A%2F%2Flocalhost%3A5000')
        except HTTPError:
            self.assertEqual(self.client.last_response.status_code, 404)

    def test_4_del_simple_key_cli(self):
        self._custoda_cli('del', 'test/cli')
        with self.assertRaises(subprocess.CalledProcessError) as e:
            self._custoda_cli('get', 'test/cli')
        self.assertIn(
            b'404 Client Error: Not Found for url',
            e.exception.output
        )

    def test_5_list_empty(self):
        cl = self.client.list_container('test')
        self.assertEqual(cl, [])

    def test_6_create_forwarded_container(self):
        self.fwd.create_container('dir')
        cl = self.admin.list_container('fwd/dir')
        self.assertEqual(cl, [])

    def test_7_delete_forwarded_container(self):
        self.fwd.delete_container('dir')
        try:
            self.admin.list_container('fwd/dir')
        except HTTPError:
            self.assertEqual(self.admin.last_response.status_code, 404)

    def test_9_loop(self):
        try:
            self.loop.list_container('test')
        except HTTPError:
            self.assertEqual(self.loop.last_response.status_code, 502)

    def test_A_enc_1_create_container(self):
        self.enc.create_container('container')
        cl = self.enc.list_container('container')
        self.assertEqual(cl, [])
        self.enc.delete_container('container')
        try:
            self.enc.list_container('container')
        except HTTPError:
            self.assertEqual(self.enc.last_response.status_code, 404)

    def test_A_enc_2_set_simple_key(self):
        self.enc.create_container('enc')
        self.enc.set_secret('enc/key', 'simple')
        key = self.admin.get_secret('enc/key')
        self.assertNotEqual(key, 'simple')
        key = self.enc.get_secret('enc/key')
        self.assertEqual(key, 'simple')

    def test_B_1_kem_create_container(self):
        self.kem.create_container('kem')
        cl = self.kem.list_container('kem')
        self.assertEqual(cl, [])
        self.kem.set_secret('kem/key', 'Protected')
        cl = self.kem.list_container('kem')
        self.assertEqual(cl, ['key'])
        value = self.kem.get_secret('kem/key')
        self.assertEqual(value, 'Protected')
        self.kem.del_secret('kem/key')
        try:
            self.kem.get_secret('kem/key')
        except HTTPError:
            self.assertEqual(self.kem.last_response.status_code, 404)
        self.kem.delete_container('kem')
        try:
            self.kem.list_container('kem')
        except HTTPError:
            self.assertEqual(self.kem.last_response.status_code, 404)

    def test_B_1_kem_space(self):
        self.kem.create_container('kem')
        cl = self.kem.list_container('kem')
        self.assertEqual(cl, [])
        self.kem.set_secret('kem/key with space', 'Protected Space')
        cl = self.kem.list_container('kem')
        self.assertEqual(cl, ['key with space'])
        value = self.kem.get_secret('kem/key with space')
        self.assertEqual(value, 'Protected Space')
        self.kem.del_secret('kem/key with space')
        try:
            self.kem.get_secret('kem/key with space')
        except HTTPError:
            self.assertEqual(self.kem.last_response.status_code, 404)
        self.kem.delete_container('kem')
        try:
            self.kem.list_container('kem')
        except HTTPError:
            self.assertEqual(self.kem.last_response.status_code, 404)


class CustodiaHTTPSTests(CustodiaTests):
    socket_url = 'https://localhost:{}'.format(find_port())
    verify_client = 'True'

    ca_cert = 'tests/ca/custodia-ca.pem'
    client_cert = 'tests/ca/custodia-client.pem'
    client_key = 'tests/ca/custodia-client.key'

    @classmethod
    def setUpClass(cls):
        super(CustodiaHTTPSTests, cls).setUpClass()
        cls.custodia_cli_args = [
            cls.pexec,
            '-Wignore',
            '-m', 'custodia.cli',
            '--debug',
            '--cafile', cls.ca_cert,
            '--certfile', cls.client_cert,
            '--keyfile', cls.client_key,
            '--server', cls.socket_url + '/secrets'
        ]

    @classmethod
    def create_client(cls, suffix, remote_user, clientcls=None):
        client = super(CustodiaHTTPSTests, cls).create_client(suffix,
                                                              remote_user,
                                                              clientcls)
        client.set_ca_cert(cls.ca_cert)
        client.set_client_cert(cls.client_cert, cls.client_key)
        return client

    def assert_ssl_error_msg(self, msg, exc):
        # CERTIFICATE_VERIFY_FAILED, SSLV3_ALERT_HANDSHAKE_FAILURE
        if msg in str(exc):
            return
        # 'certificate verify failed'
        msg = msg.lower().replace('_', ' ')
        if msg in str(exc):
            return
        self.fail(str(exc))

    def test_client_no_ca_trust(self):
        client = CustodiaSimpleClient(self.socket_url + '/forwarder')
        client.headers['REMOTE_USER'] = 'test'
        with self.assertRaises(SSLError) as e:
            client.list_container('test')
        self.assert_ssl_error_msg("CERTIFICATE_VERIFY_FAILED", e.exception)

    def test_client_no_client_cert(self):
        client = CustodiaSimpleClient(self.socket_url + '/forwarder')
        client.headers['REMOTE_USER'] = 'test'
        client.set_ca_cert(self.ca_cert)
        with self.assertRaises(SSLError) as e:
            client.list_container('test')
        self.assert_ssl_error_msg("SSLV3_ALERT_HANDSHAKE_FAILURE",
                                  e.exception)

    def test_C_client_cert_auth(self):
        # same CN as custodia-client.pem
        self.admin.set_secret('sak/client', self.test_auth_key)
        self.client.set_secret('test/key', 'VmVycnlTZWNyZXQK')

        c = self.create_client('/secrets', None)
        c.headers['CUSTODIA_CERT_AUTH'] = 'true'
        key = c.get_secret('test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')

        self.client.del_secret('test/key')
