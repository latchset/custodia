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

from requests.exceptions import HTTPError, SSLError

from custodia.client import CustodiaKEMClient, CustodiaSimpleClient
from custodia.store.sqlite import SqliteStore


def find_port(host='localhost'):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


TEST_CUSTODIA_CONF = """
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
handler = custodia.httpd.authenticators.SimpleHeaderAuth
name = REMOTE_USER

[auth:clientcert]
handler = custodia.httpd.authenticators.SimpleClientCertAuth

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
handler = custodia.forwarder.Forwarder
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
handler = custodia.httpd.authorizers.SimplePathAuthz
paths = /enc

[authz:enc_kem]
handler = custodia.message.kem.KEMKeysStore
server_keys = srvkid
store = simple
paths = /enc/kem

[/enc]
handler = custodia.secrets.Secrets
allowed_keytypes = simple kem
store = encgen
"""


TEST_SOCKET_URL = "http+unix://%2E%2Ftests%2Ftmp%2Ftest_socket"


def generate_all_keys(test_dir):
    filename = os.path.join(test_dir, 'test_mkey.conf')
    dburi = os.path.join(test_dir, 'test_secrets.db')
    key = jwk.JWK(generate='oct', size=256)
    with open(filename, 'w+') as keyfile:
        keyfile.write(key.export())

    srv_kid = "srvkid"
    cli_kid = "clikid"
    ss_key = jwk.JWK(generate='RSA', kid=srv_kid, use="sig")
    se_key = jwk.JWK(generate='RSA', kid=srv_kid, use="enc")
    store = SqliteStore({'dburi': dburi, 'table': 'secrets'})
    store.set('kemkeys/sig/%s' % srv_kid, ss_key.export())
    store.set('kemkeys/enc/%s' % srv_kid, se_key.export())

    cs_key = jwk.JWK(generate='RSA', kid=cli_kid, use="sig")
    ce_key = jwk.JWK(generate='RSA', kid=cli_kid, use="enc")
    store = SqliteStore({'dburi': dburi, 'table': 'secrets'})
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
        pexec = env.get('CUSTODIAPYTHON', sys.executable)

        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir)

        srvkeys, clikeys = generate_all_keys(cls.test_dir)

        custodia_conf = os.path.join(cls.test_dir, 'test_custodia.conf')
        with (open(custodia_conf, 'w+')) as conffile:
            t = Template(TEST_CUSTODIA_CONF)
            conf = t.substitute({'SOCKET_URL': cls.socket_url,
                                 'TEST_DIR': cls.test_dir,
                                 'TEST_AUTH_ID': cls.test_auth_id,
                                 'TEST_AUTH_KEY': cls.test_auth_key,
                                 'VERIFY_CLIENT': cls.verify_client})
            conffile.write(conf)
        test_log_file = os.path.join(cls.test_dir, 'test_log.txt')
        with (open(test_log_file, 'a')) as logfile:
            p = subprocess.Popen(
                [pexec, '-m', 'custodia.server', custodia_conf],
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

        cls.kem = cls.create_client('/enc', 'kem', CustodiaKEMClient)
        cls.kem.set_server_public_keys(*srvkeys)
        cls.kem.set_client_keys(*clikeys)

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

    def test_0_0_setup(self):
        self.admin.create_container('fwd')
        self.admin.create_container('sak')
        self.admin.set_secret('sak/' + self.test_auth_id, self.test_auth_key)
        self.admin.create_container('test')

    def test_0_create_container(self):
        self.client.create_container('test/container')

    def test_0_delete_container(self):
        self.client.delete_container('test/container')

    def test_1_set_simple_key(self):
        self.client.set_secret('test/key', 'VmVycnlTZWNyZXQK')

    def test_2_get_simple_key(self):
        key = self.client.get_secret('test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')

    def test_3_list_container(self):
        cl = self.client.list_container('test')
        self.assertEqual(cl, ["key"])

    def test_4_del_simple_key(self):
        self.client.del_secret('test/key')
        try:
            self.client.get_secret('test/key')
        except HTTPError:
            self.assertEqual(self.client.last_response.status_code, 404)

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


class CustodiaHTTPSTests(CustodiaTests):
    socket_url = 'https://localhost:{}'.format(find_port())
    verify_client = 'True'

    ca_cert = 'tests/ca/custodia-ca.pem'
    client_cert = 'tests/ca/custodia-client.pem'
    client_key = 'tests/ca/custodia-client.key'

    @classmethod
    def create_client(cls, suffix, remote_user, clientcls=None):
        client = super(CustodiaHTTPSTests, cls).create_client(suffix,
                                                              remote_user,
                                                              clientcls)
        client.set_ca_cert(cls.ca_cert)
        client.set_client_cert(cls.client_cert, cls.client_key)
        return client

    def test_client_no_ca_trust(self):
        client = CustodiaSimpleClient(self.socket_url + '/forwarder')
        client.headers['REMOTE_USER'] = 'test'
        with self.assertRaises(SSLError) as e:
            client.list_container('test')
        self.assertIn("CERTIFICATE_VERIFY_FAILED", str(e.exception))

    def test_client_no_client_cert(self):
        client = CustodiaSimpleClient(self.socket_url + '/forwarder')
        client.headers['REMOTE_USER'] = 'test'
        client.set_ca_cert(self.ca_cert)
        with self.assertRaises(SSLError) as e:
            client.list_container('test')
        self.assertIn("SSLV3_ALERT_HANDSHAKE_FAILURE", str(e.exception))

    def test_C_client_cert_auth(self):
        # same CN as custodia-client.pem
        self.admin.set_secret('sak/client', self.test_auth_key)
        self.client.set_secret('test/key', 'VmVycnlTZWNyZXQK')

        c = self.create_client('/secrets', None)
        c.headers['CUSTODIA_CERT_AUTH'] = 'true'
        key = c.get_secret('test/key')
        self.assertEqual(key, 'VmVycnlTZWNyZXQK')

        self.client.del_secret('test/key')
