# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError
from custodia.store.interface import CSStoreError
import json
import os


class Secrets(HTTPConsumer):

    def _get_key(self, namespace, trail):
        # pylint: disable=star-args
        return os.path.join(namespace, 'keys', *trail)

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

    def _namespace(self, request):
        if 'remote_user' not in request:
            raise HTTPError(403)
        return request['remote_user']

    def GET(self, request, response):
        trail = request.get('trail', [])
        ns = self._namespace(request)
        if len(trail) == 0:
            try:
                self.root.store.list(request.get('query',
                                                 dict()).get('filter', '*'))
            except CSStoreError:
                raise HTTPError(500)
        else:
            key = self._get_key(ns, trail)
            try:
                response['output'] = self.root.store.get(key)
            except CSStoreError:
                raise HTTPError(500)

    def PUT(self, request, response):
        trail = request.get('trail', [])
        ns = self._namespace(request)
        if len(trail) == 0:
            raise HTTPError(405)
        else:
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

            key = self._get_key(ns, trail)
            try:
                self.root.store.set(key, value)
            except CSStoreError:
                raise HTTPError(500)
