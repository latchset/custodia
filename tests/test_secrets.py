# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import logging
import os
import unittest
from base64 import b64encode

from custodia import log
from custodia.compat import configparser
from custodia.httpd.authorizers import UserNameSpace
from custodia.plugin import HTTPError
from custodia.secrets import Secrets
from custodia.store.sqlite import SqliteStore

CONFIG = u"""
[store:sqlite]
dburi = testdb.sqlite

[authz:secrets]

[authz:user]
"""


class SecretsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )
        cls.parser.read_string(CONFIG)
        cls.log_handlers = log.auditlog.logger.handlers[:]
        log.auditlog.logger.handlers = [logging.NullHandler()]
        cls.secrets = Secrets(cls.parser, 'authz:secrets')
        cls.secrets.root.store = SqliteStore(cls.parser, 'store:sqlite')
        cls.authz = UserNameSpace(cls.parser, 'authz:user')

    @classmethod
    def tearDownClass(cls):
        log.auditlog.logger.handlers = cls.log_handlers
        try:
            os.unlink(cls.secrets.root.store.dburi)
        except OSError:
            pass

    def check_authz(self, req):
        req['client_id'] = 'test'
        req['path'] = '/'.join([''] + req.get('trail', []))
        if self.authz.handle(req) is False:
            raise HTTPError(403)

    def DELETE(self, req, rep):
        self.check_authz(req)
        self.secrets.DELETE(req, rep)

    def GET(self, req, rep):
        self.check_authz(req)
        self.secrets.GET(req, rep)

    def POST(self, req, rep):
        self.check_authz(req)
        self.secrets.POST(req, rep)

    def PUT(self, req, rep):
        self.check_authz(req)
        self.secrets.PUT(req, rep)

    def test_0_LISTkey_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)

        self.assertEqual(err.exception.code, 404)

    def test_1_PUTKey(self):
        req = {'headers': {'Content-Type': 'application/json'},
               'remote_user': 'test',
               'trail': ['test', 'key1'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {}
        self.PUT(req, rep)

    def test_2_GETKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key1']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'], {"type": "simple", "value": "1234"})

    def test_3_LISTKeys(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'], ["key1"])

    def test_4_PUTKey_errors_400_1(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_2(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_3(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":}"simple","value":"2345"}'.encode('utf-8')}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_403(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['case', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_4_PUTKey_errors_404(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'more', 'key1'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_4_PUTKey_errors_405(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key2', ''],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_4_PUTKey_errors_409(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key3'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {'headers': {}}
        self.PUT(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_5_GETKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_5_GETkey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key0']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)

        self.assertEqual(err.exception.code, 404)

    def test_5_GETkey_errors_406(self):
        req = {'remote_user': 'test',
               'query': {'type': 'complex'},
               'trail': ['test', 'key1']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)

        self.assertEqual(err.exception.code, 406)

    def test_6_LISTkeys_errors_404_1(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'case', '']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_6_LISTkeys_errors_406_1(self):
        req = {'remote_user': 'test',
               'query': {'type': 'invalid'},
               'trail': ['test', '']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 406)

    def test_7_DELETEKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key1']}
        rep = {'headers': {}}
        self.DELETE(req, rep)

    def test_7_DELETEKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_7_DELETEKey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'nokey']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_7_DELETEKey_errors_405(self):
        req = {'remote_user': 'test'}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {'headers': {}}
        self.POST(req, rep)
        self.assertEqual(rep['code'], 201)

    def test_8_CREATEcont_erros_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_8_CREATEcont_erros_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'mid', 'container', '']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_CREATEcont_erros_405(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont_already_exists(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'exists', '']}
        rep = {}
        self.POST(req, rep)
        self.assertEqual(rep['code'], 201)
        # Try to create the container again
        self.POST(req, rep)
        self.assertEqual(rep['code'], 200)

    def test_8_DESTROYcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {'headers': {}}
        self.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)

    def test_8_DESTROYcont_erros_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_8_DESTROYcont_erros_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'mid', 'container', '']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_DESTROYcont_erros_409(self):
        self.test_1_PUTKey()
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_9_0_PUTRawKey(self):
        req = {'headers': {'Content-Type': 'application/octet-stream'},
               'remote_user': 'test',
               'trail': ['test', 'rawkey'],
               'body': '1234'.encode('utf-8')}
        rep = {'headers': {}}
        self.PUT(req, rep)

    def test_9_1_GETRawKey(self):
        req = {'headers': {'Accept': 'application/octet-stream'},
               'remote_user': 'test',
               'trail': ['test', 'rawkey']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'], '1234'.encode('utf-8'))

    def test_9_2_GETKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'rawkey']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'],
                         {"type": "simple", "value":
                          b64encode(b'1234').decode('utf-8')})

    def test_10_LIST_subcontainer_and_keys(self):
        # Create a container
        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        rep = {'headers': {}}
        self.POST(req, rep)
        self.assertEqual(rep['code'], 201)

        # Create a subcontainer over the parent container
        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', 'subcontainer', '']}
        rep = {'headers': {}}
        self.POST(req, rep)
        self.assertEqual(rep['code'], 201)

        # Create a secret over the parent container
        req = {'headers': {'Content-Type': 'application/json'},
               'remote_user': 'test',
               'trail': ['test', 'container_a', 'key2'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {}
        self.PUT(req, rep)

        # Retrieve the container_a data
        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        rep = {'headers': {}}
        self.GET(req, rep)
        # Verify that we can now distinguish between a subcontainer
        # and a key
        self.assertEqual(rep['output'], ['key2', 'subcontainer/'])
        # Clean up
        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', 'key2']}
        self.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)

        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', 'subcontainer', '']}
        self.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)

        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        self.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)

    def test_11_GET_container(self):
        # Create a container
        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        rep = {'headers': {}}
        self.POST(req, rep)
        self.assertEqual(rep['code'], 201)

        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'], [])

        req = {'remote_user': 'test',
               'trail': ['test', 'container_a']}
        rep = {'headers': {}}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
            self.assertEqual(err.exception.code, 406)

        req = {'remote_user': 'test',
               'trail': ['test', 'container_a', '']}
        self.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)
