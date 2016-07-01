# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import json
import logging
import os
import unittest

from base64 import b64decode, b64encode

from custodia import log
from custodia.httpd.authorizers import UserNameSpace
from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError
from custodia.message.common import UnallowedMessage
from custodia.message.common import UnknownMessageType
from custodia.message.formats import Validator
from custodia.store.interface import CSStoreError
from custodia.store.interface import CSStoreExists
from custodia.store.sqlite import SqliteStore


class Secrets(HTTPConsumer):

    def __init__(self, *args, **kwargs):
        super(Secrets, self).__init__(*args, **kwargs)
        self.allowed_keytypes = ['simple']
        if self.config and 'allowed_keytypes' in self.config:
            kt = self.config['allowed_keytypes'].split()
            self.allowed_keytypes = kt
        self._validator = Validator(self.allowed_keytypes)

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

    def _parse(self, request, query, name):
        return self._validator.parse(request, query, name)

    def _parse_query(self, request, name):
        # default to simple
        query = request.get('query', '')
        if len(query) == 0:
            query = {'type': 'simple', 'value': ''}
        return self._parse(request, query, name)

    def _parse_bin_body(self, request, name):
        body = request.get('body')
        if body is None:
            raise HTTPError(400)
        value = b64encode(bytes(body)).decode('utf-8')
        payload = {'type': 'simple', 'value': value}
        return self._parse(request, payload, name)

    def _parse_body(self, request, name):
        body = request.get('body')
        if body is None:
            raise HTTPError(400)
        value = json.loads(bytes(body).decode('utf-8'))
        return self._parse(request, value, name)

    def _parse_maybe_body(self, request, name):
        body = request.get('body')
        if body is None:
            value = {'type': 'simple', 'value': ''}
        else:
            value = json.loads(bytes(body).decode('utf-8'))
        return self._parse(request, value, name)

    def _parent_exists(self, default, trail):
        # check that the containers exist
        basename = self._db_container_key(trail[0], trail[:-1] + [''])
        try:
            keylist = self.root.store.list(basename)
        except CSStoreError:
            raise HTTPError(500)

        self.logger.debug('parent_exists: %s (%s, %r) -> %r',
                          basename, default, trail, keylist)

        if keylist is not None:
            return True

        # create default namespace if it is the only missing piece
        if len(trail) == 2 and default == trail[0]:
            container = self._db_container_key(default, '')
            self.root.store.span(container)
            return True

        return False

    def _format_reply(self, request, response, handler, output):
        reply = handler.reply(output)
        # special case to allow *very* simple clients
        if handler.msg_type == 'simple':
            binary = False
            accept = request.get('headers', {}).get('Accept', None)
            if accept is not None:
                types = accept.split(',')
                for t in types:
                    if t.strip() == 'application/json':
                        binary = False
                        break
                    elif t.strip() == 'application/octet-stream':
                        binary = True
            if binary is True:
                response['headers'][
                    'Content-Type'] = 'application/octet-stream'
                response['output'] = b64decode(reply['value'])
                return

        if reply is not None:
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = reply

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
        try:
            name = '/'.join(trail)
            msg = self._parse_query(request, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        default = request.get('default_namespace', None)
        basename = self._db_container_key(default, trail)
        try:
            keylist = self.root.store.list(basename)
            self.logger.debug('list %s returned %r', basename, keylist)
            if keylist is None:
                raise HTTPError(404)
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = msg.reply(keylist)
        except CSStoreError:
            raise HTTPError(500)

    def _create(self, trail, request, response):
        try:
            name = '/'.join(trail)
            msg = self._parse_maybe_body(request, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        default = request.get('default_namespace', None)
        basename = self._db_container_key(None, trail)
        try:
            if len(trail) > 2:
                ok = self._parent_exists(default, trail[:-1])
                if not ok:
                    raise HTTPError(404)

            self.root.store.span(basename)
        except CSStoreExists:
            raise HTTPError(409)
        except CSStoreError:
            raise HTTPError(500)

        output = msg.reply(None)
        if output is not None:
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = output
        response['code'] = 201

    def _destroy(self, trail, request, response):
        try:
            name = '/'.join(trail)
            msg = self._parse_maybe_body(request, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        basename = self._db_container_key(None, trail)
        try:
            keylist = self.root.store.list(basename)
            if keylist is None:
                raise HTTPError(404)
            if len(keylist) != 0:
                raise HTTPError(409)
            ret = self.root.store.cut(basename.rstrip('/'))
        except CSStoreError:
            raise HTTPError(500)

        if ret is False:
            raise HTTPError(404)

        output = msg.reply(None)
        if output is None:
            response['code'] = 204
        else:
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = output
            response['code'] = 200

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
            self.audit_key_access(action, client, key)

    def _get_key(self, trail, request, response):
        self._audit(log.AUDIT_GET_ALLOWED, log.AUDIT_GET_DENIED,
                    self._int_get_key, trail, request, response)

    def _int_get_key(self, trail, request, response):
        try:
            name = '/'.join(trail)
            handler = self._parse_query(request, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        key = self._db_key(trail)
        try:
            output = self.root.store.get(key)
            if output is None:
                raise HTTPError(404)
            self._format_reply(request, response, handler, output)
        except CSStoreError:
            raise HTTPError(500)

    def _set_key(self, trail, request, response):
        self._audit(log.AUDIT_SET_ALLOWED, log.AUDIT_SET_DENIED,
                    self._int_set_key, trail, request, response)

    def _int_set_key(self, trail, request, response):
        try:
            name = '/'.join(trail)

            content_type = request.get('headers', {}).get('Content-Type', '')
            content_type_value = content_type.split(';')[0].strip()
            if content_type_value == 'application/octet-stream':
                msg = self._parse_bin_body(request, name)
            elif content_type_value == 'application/json':
                msg = self._parse_body(request, name)
            else:
                raise ValueError('Invalid Content-Type')
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

        output = msg.reply(None)
        if output is not None:
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = output
        response['code'] = 201

    def _del_key(self, trail, request, response):
        self._audit(log.AUDIT_DEL_ALLOWED, log.AUDIT_DEL_DENIED,
                    self._int_del_key, trail, request, response)

    def _int_del_key(self, trail, request, response):
        try:
            name = '/'.join(trail)
            msg = self._parse_maybe_body(request, name)
        except Exception as e:
            raise HTTPError(406, str(e))
        key = self._db_key(trail)
        try:
            ret = self.root.store.cut(key)
        except CSStoreError:
            raise HTTPError(500)

        if ret is False:
            raise HTTPError(404)

        output = msg.reply(None)
        if output is None:
            response['code'] = 204
        else:
            response['headers'][
                'Content-Type'] = 'application/json; charset=utf-8'
            response['output'] = output
            response['code'] = 200


# unit tests
class SecretsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.log_handlers = log.auditlog.logger.handlers[:]
        log.auditlog.logger.handlers = [logging.NullHandler()]
        cls.secrets = Secrets()
        cls.secrets.root.store = SqliteStore({'dburi': 'testdb.sqlite'})
        cls.authz = UserNameSpace({})

    @classmethod
    def tearDownClass(cls):
        log.auditlog.logger.handlers = cls.log_handlers
        try:
            os.unlink('testdb.sqlite')
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
        self.assertEqual(rep['output'],
                         {"type": "simple", "value": "1234"})

    def test_3_LISTKeys(self):
        req = {'remote_user': 'test',
               'trail': ['test', '']}
        rep = {'headers': {}}
        self.GET(req, rep)
        self.assertEqual(rep['output'],
                         ["key1"])

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

    def test_8_CREATEcont_erros_409(self):
        req = {'remote_user': 'test',
               'trail': ['test', 'exists', '']}
        rep = {'headers': {}}
        self.POST(req, rep)
        with self.assertRaises(HTTPError) as err:
            self.POST(req, rep)
        self.assertEqual(err.exception.code, 409)

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
