# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import logging

logger = logging.getLogger(__name__)


class CSStoreError(Exception):
    def __init__(self, message=None):
        logger.debug(message)
        super(CSStoreError, self).__init__(message)


class CSStoreExists(Exception):
    def __init__(self, message=None):
        logger.debug(message)
        super(CSStoreExists, self).__init__(message)


class CSStore(object):

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, replace=False):
        raise NotImplementedError

    def span(self, key):
        raise NotImplementedError

    def list(self, keyfilter=None):
        raise NotImplementedError

    def cut(self, key):
        raise NotImplementedError
