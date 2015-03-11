# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import json
from custodia.http.consumer import HTTPConsumer


class Root(HTTPConsumer):

    def GET(self, request, response):
        return json.dumps({'message': "Quis custodiet ipsos custodes?"})
