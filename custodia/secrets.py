# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError
from custodia.store.interface import CSStoreError
import json
import os


class Secrets(HTTPConsumer):

    def _get_key(self, namespaces, trail):
        # Check tht the keys is in one of the authorized namespaces
        if len(trail) < 1 or trail[0] not in namespaces:
            raise HTTPError(403)
        # pylint: disable=star-args
        return os.path.join('keys', *trail)

    def _get_filter(self, namespaces, trail, userfilter):
        f = None
        if len(trail) > 0:
            for ns in namespaces:
                if ns == trail[0]:
                    f = self._get_key(namespaces, trail)
                break
        if f is None:
            # Consider the first namespace as the default one
            t = [namespaces[0]] + trail
            f = self._get_key(namespaces, t)
        return '%s/%s' % (f, userfilter)

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

    def GET(self, request, response):
        trail = request.get('trail', [])
        ns = self._namespaces(request)
        if len(trail) == 0 or trail[-1] == '':
            try:
                userfilter = request.get('query', dict()).get('filter', '')
                keyfilter = self._get_filter(ns, trail[:-1], userfilter)
                keydict = self.root.store.list(keyfilter)
                if keydict is None:
                    raise HTTPError(404)
                output = dict()
                for k in keydict:
                    # strip away the internal prefix for storing keys
                    name = k[len('keys/'):]
                    output[name] = json.loads(keydict[k])
                response['output'] = json.dumps(output)
            except CSStoreError:
                raise HTTPError(404)
        else:
            key = self._get_key(ns, trail)
            try:
                output = self.root.store.get(key)
                if output is None:
                    raise HTTPError(404)
                response['output'] = output
            except CSStoreError:
                raise HTTPError(500)

    def PUT(self, request, response):
        trail = request.get('trail', [])
        ns = self._namespaces(request)
        if len(trail) == 0 or trail[-1] == '':
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
