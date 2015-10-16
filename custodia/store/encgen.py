# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from jwcrypto.common import json_decode, json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK

from custodia.store.interface import CSStore, CSStoreError


class EncryptedOverlay(CSStore):

    def __init__(self, config):
        super(EncryptedOverlay, self).__init__(config)

        if 'backing_store' not in config:
            raise ValueError('Missing "backing_store" for Encrypted Store')
        self.store_name = config['backing_store']
        self.store = None

        if 'master_key' not in config:
            raise ValueError('Missing "master_key" for Encrypted Store')

        with open(config['master_key']) as f:
            data = f.read()
            key = json_decode(data)
            self.mkey = JWK(**key)

        self.enc = config.get('master_enctype', 'A256CBC_HS512')

    def get(self, key):
        value = self.store.get(key)
        if value is None:
            return None
        try:
            jwe = JWE()
            jwe.deserialize(value, self.mkey)
            return jwe.payload.decode('utf-8')
        except Exception as err:
            self.logger.error("Error parsing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to parse key')

    def set(self, key, value, replace=False):
        jwe = JWE(value, json_encode({'alg': 'dir', 'enc': self.enc}))
        jwe.add_recipient(self.mkey)
        cvalue = jwe.serialize(compact=True)
        return self.store.set(key, cvalue, replace)

    def span(self, key):
        return self.store.span(key)

    def list(self, keyfilter=''):
        return self.store.list(keyfilter)

    def cut(self, key):
        return self.store.cut(key)
