# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError
from custodia.store.interface import CSStoreError
from custodia.store.interface import CSStoreExists
import json
import os


class Secrets(HTTPConsumer):

    def _db_key(self, namespaces, trail):
        # Check tht the keys is in one of the authorized namespaces
        if len(trail) < 1 or trail[0] not in namespaces:
            raise HTTPError(403)
        # pylint: disable=star-args
        return os.path.join('keys', *trail)

    def _db_container_key(self, namespaces, trail):
        f = None
        if len(trail) > 0:
            for ns in namespaces:
                if ns == trail[0]:
                    f = self._db_key(namespaces, trail + [''])
                break
            if f is None:
                raise HTTPError(403)
        else:
            # Consider the first namespace as the default one
            t = [namespaces[0]] + trail + ['']
            f = self._db_key(namespaces, t)
        return f

    def _validate(self, value):
        try:
            msg = json.loads(value)
        except Exception:
            raise ValueError('Invalid JSON in payload')
        if 'type' not in msg:
            raise ValueError('Message type missing')
        if msg['type'] != 'simple':
            raise ValueError('Message type unknown')
        if 'value' not in msg:
            raise ValueError('Message value missing')
        if len(msg.keys()) != 2:
            raise ValueError('Unknown attributes in Message')

    def _namespaces(self, request):
        if 'remote_user' not in request:
            raise HTTPError(403)
        # At the moment we just have one namespace, the user's name
        return [request['remote_user']]

    def _parent_exists(self, ns, trail):
        # check that the containers exist
        exists = True
        n = 0
        for n in range(1, len(trail)):
            probe = self._db_key(ns, trail[:n] + [''])
            try:
                check = self.root.store.get(probe)
                if check is None:
                    exists = False
                    break
            except CSStoreError:
                exists = False
                break

        # create if default namespace
        if not exists and len(trail) == 2 and n == 1 and ns[0] == trail[0]:
            self.root.store.set(probe, '')
            exists = True

        return exists

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
        ns = self._namespaces(request)
        try:
            basename = self._db_container_key(ns, trail[:-1])
            userfilter = request.get('query', dict()).get('filter', '')
            keydict = self.root.store.list(basename + userfilter)
            if keydict is None:
                raise HTTPError(404)
            output = dict()
            for k in keydict:
                # remove the base container itself
                if k == basename:
                    continue
                # strip away the internal prefix for storing keys
                name = k[len('keys/'):]
                # return empty value for containers
                if name.endswith('/'):
                    output[name] = ''
                else:
                    output[name] = json.loads(keydict[k])
            response['output'] = json.dumps(output)
        except CSStoreError:
            raise HTTPError(404)

    def _create(self, trail, request, response):
        ns = self._namespaces(request)
        basename = self._db_container_key(ns, trail[:-1])
        try:
            ok = self._parent_exists(ns, trail[:-1])
            if not ok:
                raise HTTPError(404)

            self.root.store.set(basename, '')
        except CSStoreExists:
            raise HTTPError(409)
        except CSStoreError:
            raise HTTPError(500)

        response['code'] = 201

    def _destroy(self, trail, request, response):
        ns = self._namespaces(request)
        basename = self._db_container_key(ns, trail[:-1])
        try:
            keydict = self.root.store.list(basename)
            if keydict is None:
                raise HTTPError(404)
            keys = list(keydict.keys())
            if len(keys) != 1:
                raise HTTPError(409)
            if keys[0] != basename:
                # uh ?
                raise HTTPError(409)
            print((basename, keys))
            ret = self.root.store.cut(basename)
        except CSStoreError:
            ret = False

        if ret is False:
            raise HTTPError(404)

        response['code'] = 204

    def _get_key(self, trail, request, response):
        ns = self._namespaces(request)
        key = self._db_key(ns, trail)
        try:
            output = self.root.store.get(key)
            if output is None:
                raise HTTPError(404)
            response['output'] = output
        except CSStoreError:
            raise HTTPError(500)

    def _set_key(self, trail, request, response):
        ns = self._namespaces(request)
        content_type = request.get('headers',
                                   dict()).get('Content-Type', '')
        if content_type.split(';')[0].strip() != 'application/json':
            raise HTTPError(400, 'Invalid Content-Type')
        body = request.get('body')
        if body is None:
            raise HTTPError(400)
        value = bytes(body).decode('utf-8')
        try:
            self._validate(value)
        except ValueError as e:
            raise HTTPError(400, str(e))

        # must _db_key first as access control is done here for now
        # otherwise users would e able to probe containers in namespaces
        # they do not have access to.
        key = self._db_key(ns, trail)

        try:
            ok = self._parent_exists(ns, trail)
            if not ok:
                raise HTTPError(404)

            ok = self.root.store.set(key, value)
        except CSStoreExists:
            raise HTTPError(409)
        except CSStoreError:
            raise HTTPError(500)

        response['code'] = 201

    def _del_key(self, trail, request, response):
        ns = self._namespaces(request)
        key = self._db_key(ns, trail)
        try:
            ret = self.root.store.cut(key)
        except CSStoreError:
            ret = False

        if ret is False:
            raise HTTPError(404)

        response['code'] = 204

# unit tests
import unittest
from custodia.store.sqlite import SqliteStore


class SecretsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.secrets = Secrets()
        cls.secrets.root.store = SqliteStore({'dburi': 'testdb.sqlite'})

    @classmethod
    def tearDownClass(self):
        try:
            os.unlink('testdb.sqlite')
        except OSError:
            pass

    def test_0_LISTkey_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.GET(req, rep)

        self.assertEqual(err.exception.code, 404)

    def test_1_PUTKey(self):
        req = {'headers': {'Content-Type': 'application/json'},
               'remote_user': 'test',
               'trail': ['test', 'key1'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {}
        self.secrets.PUT(req, rep)

    def test_2_GETKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key1']}
        rep = {}
        self.secrets.GET(req, rep)
        self.assertEqual(rep['output'],
                         '{"type":"simple","value":"1234"}')

    def test_3_LISTKeys(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        self.secrets.GET(req, rep)
        self.assertEqual(json.loads(rep['output']),
                         json.loads('{"test/key1":'
                                    '{"type":"simple","value":"1234"}}'))

    def test_3_LISTKeys_2(self):
        req = {'remote_user': 'test',
               'query': {'filter': 'key'},
               'trail': ['test', '']}
        rep = {}
        self.secrets.GET(req, rep)
        self.assertEqual(json.loads(rep['output']),
                         json.loads('{"test/key1":'
                                    '{"type":"simple","value":"1234"}}'))

    def test_4_PUTKey_errors_400_1(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_2(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_400_3(self):
        req = {'headers': {'Content-Type': 'text/plain'},
               'remote_user': 'test',
               'trail': ['test', 'key2'],
               'body': '{"type":}"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 400)

    def test_4_PUTKey_errors_403(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['case', 'key2'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_4_PUTKey_errors_404(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'more', 'key1'],
               'body': '{"type":"simple","value":"1234"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_4_PUTKey_errors_405(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key2', ''],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_4_PUTKey_errors_409(self):
        req = {'headers': {'Content-Type': 'application/json; charset=utf-8'},
               'remote_user': 'test',
               'trail': ['test', 'key3'],
               'body': '{"type":"simple","value":"2345"}'.encode('utf-8')}
        rep = {}
        self.secrets.PUT(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.secrets.PUT(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_5_GETKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.GET(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_5_GETkey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key0']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.GET(req, rep)

        self.assertEqual(err.exception.code, 404)

    def test_6_LISTkeys_errors_404_1(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'case', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.GET(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_6_LISTkeys_errors_404_2(self):
        req = {'remote_user': 'test',
               'query': {'filter': 'foo'},
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.GET(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_7_DELETEKey(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'key1']}
        rep = {}
        self.secrets.DELETE(req, rep)

    def test_7_DELETEKey_errors_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'key1']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_7_DELETEKey_errors_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'nokey']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_7_DELETEKey_errors_405(self):
        req = {'remote_user': 'test'}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {}
        self.secrets.POST(req, rep)
        self.assertEqual(rep['code'], 201)

    def test_8_CREATEcont_erros_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.POST(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_8_CREATEcont_erros_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'mid', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.POST(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_CREATEcont_erros_405(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.POST(req, rep)
        self.assertEqual(err.exception.code, 405)

    def test_8_CREATEcont_erros_409(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'exists', '']}
        rep = {}
        self.secrets.POST(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.secrets.POST(req, rep)
        self.assertEqual(err.exception.code, 409)

    def test_8_DESTROYcont(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'container', '']}
        rep = {}
        self.secrets.DELETE(req, rep)
        self.assertEqual(rep['code'], 204)

    def test_8_DESTROYcont_erros_403(self):
        req = {'remote_user': 'case',
               'trail': ['test', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 403)

    def test_8_DESTROYcont_erros_404(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'mid', 'container', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 404)

    def test_8_DESTROYcont_erros_409(self):
        self.test_1_PUTKey()
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {}
        with self.assertRaises(HTTPError) as err:
            self.secrets.DELETE(req, rep)
        self.assertEqual(err.exception.code, 409)
