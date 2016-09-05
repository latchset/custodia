# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import print_function

try:
    from etcd import (Client, EtcdException, EtcdNotFile, EtcdAlreadyExist,
                      EtcdKeyNotFound)
except ImportError:
    def Client(*args, **kwargs):
        raise RuntimeError("Etcd client is unavailable")

    class EtcdException(Exception):
        pass

    class EtcdNotFile(Exception):
        pass

    class EtcdKeyNotFound(Exception):
        pass

    class EtcdAlreadyExist(Exception):
        pass

from custodia.plugin import CSStore, CSStoreError, CSStoreExists
from custodia.plugin import PluginOption


class EtcdStore(CSStore):
    etcd_server = PluginOption(str, '127.0.0.1', None)
    etcd_port = PluginOption(int, '4001', None)
    namespace = PluginOption(str, '/custodia', None)

    def __init__(self, config, section):
        super(EtcdStore, self).__init__(config, section)
        # Initialize the DB by trying to create the default table
        try:
            self.etcd = Client(self.etcd_server, self.etcd_port)
            self.etcd.write(self.namespace, None, dir=True)
        except EtcdNotFile:
            # Already exists
            pass
        except EtcdException:
            self.logger.exception("Error creating namespace %s",
                                  self.namespace)
            raise CSStoreError('Error occurred while trying to init db')

    def _absolute_key(self, key):
        """Get absolute path to key and validate key"""
        if '//' in key:
            raise ValueError("Invalid empty components in key '%s'" % key)
        parts = key.split('/')
        if set(parts).intersection({'.', '..'}):
            raise ValueError("Invalid relative components in key '%s'" % key)
        return '/'.join([self.namespace] + parts).replace('//', '/')

    def get(self, key):
        self.logger.debug("Fetching key %s", key)
        try:
            result = self.etcd.get(self._absolute_key(key))
        except EtcdException:
            self.logger.exception("Error fetching key %s", key)
            raise CSStoreError('Error occurred while trying to get key')
        self.logger.debug("Fetched key %s got result: %r", key, result)
        return result.value  # pylint: disable=no-member

    def set(self, key, value, replace=False):
        self.logger.debug("Setting key %s to value %s (replace=%s)",
                          key, value, replace)
        path = self._absolute_key(key)
        try:
            self.etcd.write(path, value, prevExist=replace)
        except EtcdAlreadyExist as err:
            raise CSStoreExists(str(err))
        except EtcdException:
            self.logger.exception("Error storing key %s", key)
            raise CSStoreError('Error occurred while trying to store key')

    def span(self, key):
        path = self._absolute_key(key)
        self.logger.debug("Creating directory %s", path)
        try:
            self.etcd.write(path, None, dir=True, prevExist=False)
        except EtcdAlreadyExist as err:
            raise CSStoreExists(str(err))
        except EtcdException:
            self.logger.exception("Error storing key %s", key)
            raise CSStoreError('Error occurred while trying to store key')

    def list(self, keyfilter='/'):
        path = self._absolute_key(keyfilter)
        if path != '/':
            path = path.rstrip('/')
        self.logger.debug("Listing keys matching %s", path)
        try:
            result = self.etcd.read(path, recursive=True)
        except EtcdKeyNotFound:
            return None
        except EtcdException:
            self.logger.exception("Error listing %s", keyfilter)
            raise CSStoreError('Error occurred while trying to list keys')
        self.logger.debug("Searched for %s got result: %r", path, result)
        value = set()
        for entry in result.get_subtree():
            if entry.key == path:
                continue
            name = entry.key[len(path):]
            if entry.dir and not name.endswith('/'):
                name += '/'
            value.add(name.lstrip('/'))
        return sorted(value)

    def cut(self, key):
        self.logger.debug("Removing key %s", key)
        try:
            self.etcd.delete(self._absolute_key(key))
        except EtcdKeyNotFound:
            self.logger.debug("Key %s not found", key)
            return False
        except EtcdException:
            self.logger.exception("Error removing key %s", key)
            raise CSStoreError('Error occurred while trying to cut key')
        self.logger.debug("Key %s removed", key)
        return True
