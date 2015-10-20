# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import json
import uuid

from custodia.client import CustodiaHTTPClient
from custodia.httpd.consumer import HTTPConsumer
from custodia.httpd.server import HTTPError


class Forwarder(HTTPConsumer):

    def __init__(self, *args, **kwargs):
        super(Forwarder, self).__init__(*args, **kwargs)
        self.client = CustodiaHTTPClient(self.config['forward_uri'])
        self.headers = json.loads(self.config.get('forward_headers', '{}'))
        self.use_prefix = self.config.get('prefix_remote_user', True)
        self.uuid = str(uuid.uuid4())
        self.headers['X-LOOP-CUSTODIA'] = self.uuid

    def _path(self, request):
        trail = request.get('trail', [])
        if self.use_prefix:
            prefix = [request.get('remote_user', 'guest').rstrip('/')]
        else:
            prefix = []
        return '/'.join(prefix + trail)

    def _headers(self, request):
        headers = {}
        headers.update(self.headers)
        loop = request['headers'].get('X-LOOP-CUSTODIA', None)
        if loop is not None:
            headers['X-LOOP-CUSTODIA'] += ',' + loop
        return headers

    def _response(self, reply, response):
        if reply.status_code < 200 or reply.status_code > 299:
            raise HTTPError(reply.status_code)
        response['code'] = reply.status_code
        if reply.content:
            response['output'] = reply.content

    def _request(self, cmd, request, response, path, **kwargs):
        if self.uuid in request['headers'].get('X-LOOP-CUSTODIA', ''):
            raise HTTPError(502, "Loop detected")
        reply = cmd(path, **kwargs)
        self._response(reply, response)

    def GET(self, request, response):
        self._request(self.client.get, request, response,
                      self._path(request),
                      params=request.get('query', None),
                      headers=self._headers(request))

    def PUT(self, request, response):
        self._request(self.client.put, request, response,
                      self._path(request),
                      data=request.get('body', None),
                      params=request.get('query', None),
                      headers=self._headers(request))

    def DELETE(self, request, response):
        self._request(self.client.delete, request, response,
                      self._path(request),
                      params=request.get('query', None),
                      headers=self._headers(request))

    def POST(self, request, response):
        self._request(self.client.post, request, response,
                      self._path(request),
                      data=request.get('body', None),
                      params=request.get('query', None),
                      headers=self._headers(request))
