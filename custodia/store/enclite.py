# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import logging

from jwcrypto.common import json_decode, json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK

from custodia.store.interface import CSStoreError
from custodia.store.sqlite import SqliteStore

logger = logging.getLogger(__name__)


class EncryptedStore(SqliteStore):

    def __init__(self, config):

        super(EncryptedStore, self).__init__(config)

        if 'master_key' not in config:
            raise ValueError('Missing "master_key" for Encrypted Store')

        with open(config['master_key']) as f:
            data = f.read()
            key = json_decode(data)
            self.mkey = JWK(**key)

        if 'master_enctype' in config:
            self.enc = config['master_enctype']
        else:
            self.enc = 'A256CBC_HS512'

    def get(self, key):
        value = super(EncryptedStore, self).get(key)
        if value is None:
            return None
        try:
            jwe = JWE()
            jwe.deserialize(value, self.mkey)
            return jwe.payload.decode('utf-8')
        except Exception:
            logger.exception("Error parsing key %s", key)
            raise CSStoreError('Error occurred while trying to parse key')

    def set(self, key, value, replace=False):
        jwe = JWE(value, json_encode({'alg': 'dir', 'enc': self.enc}))
        jwe.add_recipient(self.mkey)
        cvalue = jwe.serialize(compact=True)
        return super(EncryptedStore, self).set(key, cvalue, replace)
