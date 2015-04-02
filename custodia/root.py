# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.httpd.consumer import HTTPConsumer
from custodia.secrets import Secrets
import json


class Root(HTTPConsumer):

    def __init__(self, *args, **kwargs):
        super(Root, self).__init__(*args, **kwargs)
        if self.store_name is not None:
            self.add_sub('secrets', Secrets())

    def GET(self, request, response):
        return json.dumps({'message': "Quis custodiet ipsos custodes?"})
