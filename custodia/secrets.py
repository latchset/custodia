# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import json
import os
import unittest

from custodia import log
from custodia.httpd.authorizers import HTTPAuthorizer
from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError
from custodia.message.common import UnallowedMessage
from custodia.message.common import UnknownMessageType
from custodia.message.formats import Validator
from custodia.store.interface import CSStoreError
from custodia.store.interface import CSStoreExists
from custodia.store.sqlite import SqliteStore


class Namespaces(HTTPAuthorizer):

    def __init__(self, *args, **kwargs):
        super(Namespaces, self).__init__(*args, **kwargs)
        self.path = self.config.get('path', '/')
        # warn if self.path does not end with '/' ?

    def handle(self, request):

        # First of all check we are in the right path
        path = request.get('path', '/')
        if not path.startswith(self.path):
            return None

        if 'remote_user' not in request:
            return False
        # At the moment we just have one namespace, the user's name
        namespaces = [request['remote_user']]

        # Check the request is in a valid namespace
        trail = request.get('trail', [])
        if len(trail) > 0 and trail[0] != namespaces[0]:
            return False

        request['default_namespace'] = namespaces[0]
        return True


class Secrets(HTTPConsumer):

    def __init__(self, *args, **kwargs):
        super(Secrets, self).__init__(*args, **kwargs)
        self.allowed_keytypes = ['simple']
        if self.config and 'allowed_keytypes' in self.config:
            kt = self.config['allowed_keytypes'].split()
            self.allowed_keytypes = kt
        self._validator = Validator(self.allowed_keytypes)
        self._auditlog = log.AuditLog(self.config)

    def _db_key(self, trail):
        if len(trail) < 2:
            raise HTTPError(403)
        return os.path.join('keys', *trail)

    def _db_container_key(self, default, trail):
        f = None
        if len(trail) > 1:
            f = self._db_key(trail)
        elif len(trail) == 1 and trail[0] != '':
            raise HTTPError(403)
        elif default is None:
            # No dfault namespace, fail
            raise HTTPError(403)
        else:
            # Use the default namespace
            f = self._db_key([default, ''])
        return f

    def _parse(self, request, value, name):
        return self._validator.parse(request, value, name)

    def _parent_exists(self, default, trail):
        # check that the containers exist
        basename = self._db_container_key(trail[0], '')
        try:
            keylist = self.root.store.list(basename)
        except CSStoreError:
            raise HTTPError(500)

        # create default namespace if it is the only missing piece
        if keylist is None and len(trail) == 2 and default == trail[0]:
            container = self._db_container_key(default, '')
            self.root.store.set(container, '')
            return True

        # check if any parent is missing
        for n in range(1, len(trail)):
            c = self._db_key(trail[:n] + [''])
            if c not in keylist:
                return False

        return True

    def GET(self, request, response):
        trail = request.get('trail', [])
        if len(trail) == 0 or trail[-1] == '':
            self._list(trail, request, response)
        else:
            self._get_key(trail, request, response)

    def PUT(self, request, response):
        trail = request.get('trail', [])
        if len(trail) == 0 or trail[-1] == '':
            raise HTTPError(405)
        else:
            self._set_key(trail, request, response)

    def DELETE(self, request, response):
        trail = request.get('trail', [])
        if len(trail) == 0:
            raise HTTPError(405)
        if trail[-1] == '':
            self._destroy(trail, request, response)
        else:
            self._del_key(trail, request, response)

    def POST(self, request, response):
        trail = request.get('trail', [])
        if len(trail) > 0 and trail[-1] == '':
            self._create(trail, request, response)
        else:
            raise HTTPError(405)

    def _list(self, trail, request, response):
        default = request.get('default_namespace', None)
        basename = self._db_container_key(default, trail)
        userfilter = request.get('query', dict()).get('filter', '')
        try:
            keylist = self.root.store.list(basename + userfilter)
            if keylist is None:
                raise HTTPError(404)
            # remove the base container itself
            output = list()
            for k in keylist:
                if k == basename:
                    continue
                # strip away the internal prefix for storing keys
                name = k[len('keys/'):]
                output.append(name)
            response['output'] = json.dumps(output)
        except CSStoreError:
            raise HTTPError(500)

    def _create(self, trail, request, response):
        default = request.get('default_namespace', None)
        basename = self._db_container_key(None, trail)
        try:
            ok = self._parent_exists(default, trail[:-1])
            if not ok:
                raise HTTPError(404)

            self.root.store.set(basename, '')
        except CSStoreExists:
            raise HTTPError(409)
        except CSStoreError:
            raise HTTPError(500)

        response['code'] = 201

    def _destroy(self, trail, request, response):
        basename = self._db_container_key(None, trail)
        try:
            keylist = self.root.store.list(basename)
            if keylist is None:
                raise HTTPError(404)
            if basename not in keylist:
                # uh ?
                raise HTTPError(409)
            if len(keylist) != 1:
                raise HTTPError(409)
            ret = self.root.store.cut(basename)
        except CSStoreError:
            raise HTTPError(500)

        if ret is False:
            raise HTTPError(404)

        response['code'] = 204

    def _client_name(self, request):
        if 'remote_user' in request:
            return request['remote_user']
        elif 'creds' in request:
            creds = request['creds']
            return '<pid={pid:d} uid={uid:d} gid={gid:d}>'.format(**creds)
        else:
            return 'Unknown'

    def _audit(self, ok, fail, fn, trail, request, response):
        action = fail
        client = self._client_name(request)
        key = '/'.join(trail)
        try:
            fn(trail, request, response)
            action = ok
        finally:
            self._auditlog.key_access(action, client, key)

    def _get_key(self, trail, request, response):
        self._audit(log.AUDIT_GET_ALLOWED, log.AUDIT_GET_DENIED,
                    self._int_get_key, trail, request, response)

    def _int_get_key(self, trail, request, response):
        # default to simple
        query = request.get('query', '')
        if len(query) == 0:
            query = {'type': 'simple', 'value': ''}
        try:
            name = '/'.join(trail)
            msg = self._parse(request, query, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        key = self._db_key(trail)
        try:
            output = self.root.store.get(key)
            if output is None:
                raise HTTPError(404)
            response['output'] = msg.reply(output)
        except CSStoreError:
            raise HTTPError(500)

    def _set_key(self, trail, request, response):
        self._audit(log.AUDIT_SET_ALLOWED, log.AUDIT_SET_DENIED,
                    self._int_set_key, trail, request, response)

    def _int_set_key(self, trail, request, response):
        content_type = request.get('headers',
                                   dict()).get('Content-Type', '')
        if content_type.split(';')[0].strip() != 'application/json':
            raise HTTPError(400, 'Invalid Content-Type')
        body = request.get('body')
        if body is None:
            raise HTTPError(400)
        value = bytes(body).decode('utf-8')
        try:
            name = '/'.join(trail)
            msg = self._parse(request, json.loads(value), name)
        except UnknownMessageType as e:
            raise HTTPError(406, str(e))
        except UnallowedMessage as e:
            raise HTTPError(406, str(e))
        except Exception as e:
            raise HTTPError(400, str(e))

        # must _db_key first as access control is done here for now
        # otherwise users would e able to probe containers in namespaces
        # they do not have access to.
        key = self._db_key(trail)

        try:
            default = request.get('default_namespace', None)
            ok = self._parent_exists(default, trail)
            if not ok:
                raise HTTPError(404)

            ok = self.root.store.set(key, msg.payload)
        except CSStoreExists:
            raise HTTPError(409)
        except CSStoreError:
            raise HTTPError(500)

        response['code'] = 201

    def _del_key(self, trail, request, response):
        self._audit(log.AUDIT_DEL_ALLOWED, log.AUDIT_DEL_DENIED,
                    self._int_del_key, trail, request, response)

    def _int_del_key(self, trail, request, response):
        key = self._db_key(trail)
        try:
            ret = self.root.store.cut(key)
        except CSStoreError:
            raise HTTPError(500)

        if ret is False:
            raise HTTPError(404)

        response['code'] = 204


# unit tests
class SecretsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.secrets = Secrets({'auditlog': 'test.audit.log'})
        cls.secrets.root.store = SqliteStore({'dburi': 'testdb.sqlite'})
        cls.authz = Namespaces({})

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink('test.audit.log')
            os.unlink('testdb.sqlite')
        except OSError:
            pass

    def check_authz(self, req):
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
        rep = {}
        self.GET(req, rep)
        self.assertEqual(json.loads(rep['output']),
                         {"type": "simple", "value": "1234"})

    def test_3_LISTKeys(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        self.GET(req, rep)
        self.assertEqual(json.loads(rep['output']),
                         json.loads('["test/key1"]'))

    def test_3_LISTKeys_2(self):
        req = {'remote_user': 'test',
               'query': {'filter': 'key'},
               'trail': ['test', '']}
        rep = {}
        self.GET(req, rep)
        self.assertEqual(json.loads(rep['output']),
                         json.loads('["test/key1"]'))

    def test_4_PUTKey_errors_400_1(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_2(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_3(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":}"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_403(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['case', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_4_PUTKey_errors_404(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'more', 'key1'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_4_PUTKey_errors_405(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key2', ''],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_4_PUTKey_errors_409(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key3'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        self.PUT(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.PUT(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_5_GETKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_5_GETkey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key0']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)

        self.assertEqual(err.exception.code, 404)

    def test_5_GETkey_errors_406(self):
        req = {'remote_user': 'test',
               'query': {'type': 'complex'},
               'trail': ['test', 'key1']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)

        self.assertEqual(err.exception.code, 406)

    def test_6_LISTkeys_errors_404_1(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'case', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_6_LISTkeys_errors_404_2(self):
        req = {'remote_user': 'test',
               'query': {'filter': 'foo'},
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.GET(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_7_DELETEKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key1']}
        rep = {}
        self.DELETE(req, rep)

    def test_7_DELETEKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_7_DELETEKey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'nokey']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_7_DELETEKey_errors_405(self):
        req = {'remote_user': 'test'}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {}
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
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_CREATEcont_erros_405(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont_erros_409(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'exists', '']}
        rep = {}
        self.POST(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_8_DESTROYcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {}
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
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_DESTROYcont_erros_409(self):
        self.test_1_PUTKey()
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.DELETE(req, rep)
        self.assertEqual(err.exception.code, 409)
