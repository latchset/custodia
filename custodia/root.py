# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import cherrypy
import json


class Root(object):

    def __init__(self):
        print "started"

    @cherrypy.expose
    def index(self):
        return json.dumps({'message': "Quis custodiet ipsos custodes?"})
