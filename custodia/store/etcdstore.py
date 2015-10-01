# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import print_function

import sys

import etcd

from custodia.store.interface import CSStore, CSStoreError, CSStoreExists


def log_error(error):
    print(error, file=sys.stderr)


class EtcdStore(CSStore):

    def __init__(self, config):
        self.server = config.get('etcd_server', '127.0.0.1')
        self.port = int(config.get('etcd_port', 4001))
        self.namespace = config.get('namespace', "/custodia")

        # Initialize the DB by trying to create the default table
        try:
            self.etcd = etcd.Client(self.server, self.port)
            self.etcd.write(self.namespace, None, dir=True)
        except etcd.EtcdNotFile:
            # Already exists
            pass
        except etcd.EtcdException as err:
            log_error("Error creating namespace %s: [%r]" % (self.namespace,
                                                             repr(err)))
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
        try:
            result = self.etcd.get(self._absolute_key(key))
        except etcd.EtcdException as err:
            log_error("Error fetching key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to get key')
        return result.value

    def set(self, key, value, replace=False):
        path = self._absolute_key(key)
        try:
            self.etcd.write(path, value, prevExist=replace)
        except etcd.EtcdAlreadyExist as err:
            raise CSStoreExists(str(err))
        except etcd.EtcdException as err:
            log_error("Error storing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to store key')

    def span(self, key):
        path = self._absolute_key(key)
        try:
            self.etcd.write(path, None, dir=True, prevExist=False)
        except etcd.EtcdAlreadyExist as err:
            raise CSStoreExists(str(err))
        except etcd.EtcdException as err:
            log_error("Error storing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to store key')

    def list(self, keyfilter='/'):
        path = self._absolute_key(keyfilter)
        if path != '/':
            path = path.rstrip('/')
        try:
            result = self.etcd.read(path, recursive=True)
        except etcd.EtcdKeyNotFound:
            return None
        except etcd.EtcdException as err:
            log_error("Error listing %s: [%r]" % (keyfilter, repr(err)))
            raise CSStoreError('Error occurred while trying to list keys')

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
        try:
            self.etcd.delete(self._absolute_key(key))
        except etcd.EtcdKeyNotFound:
            return False
        except etcd.EtcdException as err:
            log_error("Error removing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to cut key')
        return True
