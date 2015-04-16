# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file


class InvalidMessage(Exception):
    """Invalid Message.

    This exception is raised when a message cannot be parsed
    or validated.
    """
    pass


class UnknownMessageType(Exception):
    """Unknown Message Type.

    This exception is raised when a message is of an unknown
    type.
    """
    pass


class UnallowedMessage(Exception):
    """Unallowed Message.

    This exception is raise when the message type is know but
    is not allowed.
    """
    pass


class MessageHandler(object):

    def __init__(self, request):
        self.req = request
        self.payload = None

    def parse(self, msg):
        """Parses the message.

        :param req: the original request
        :param msg: a decoded json string with the incoming message

        :raises InvalidMessage: if the message cannot be parsed or validated
        """

        raise NotImplementedError

    def reply(self, output):
        """Generates a reply.

        :param req: the original request
        :param output: a json string with the stored output payload
        """

        raise NotImplementedError
