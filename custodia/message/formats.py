# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from custodia.message.common import InvalidMessage
from custodia.message.common import UnknownMessageType
from custodia.message.common import UnallowedMessage
from custodia.message.simple import SimpleKey


default_types = ['simple']

key_types = {'simple': SimpleKey}


class Validator(object):
    """Validates incoming messages."""

    def __init__(self, allowed=None):
        """Creates a Validator object.

        :param allowed: list of allowed message types (optional)
        """
        self.allowed = allowed or default_types
        self.types = dict()
        for t in self.allowed:
            self.types[t] = key_types[t]

    def add_types(self, types):
        self.types.update(types)

    def parse(self, request, msg):
        if not isinstance(msg, dict):
            raise InvalidMessage('The message must be a dict')

        if 'type' not in msg:
            raise InvalidMessage('The type is missing')

        if 'value' not in msg:
            raise InvalidMessage('The value is missing')

        if msg['type'] not in list(self.types.keys()):
            raise UnknownMessageType("Type '%s' is unknown" % msg['type'])

        if msg['type'] not in self.allowed:
            raise UnallowedMessage("Message type '%s' not allowed" % (
                                   msg['type'],))

        handler = self.types[msg['type']](request)
        handler.parse(msg['value'])
        return handler
