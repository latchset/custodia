# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os

from jwcrypto.common import json_decode, json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK

from custodia.plugin import CSStore, CSStoreError


class EncryptedOverlay(CSStore):
    """Encrypted overlay for storage backends

    Arguments:
        backing_store (required):
            name of backing storage
        master_key (required)
            path to master key (JWK JSON)
        autogen_master_key (default: false)
            auto-generate key file if missing?
        master_enctype (default: A256CBC_HS512)
            JWE algorithm name
    """
    key_sizes = {
        'A128CBC-HS256': 256,
        'A256CBC-HS512': 512,
    }

    def __init__(self, config):
        super(EncryptedOverlay, self).__init__(config)

        if 'backing_store' not in config:
            raise ValueError('Missing "backing_store" for Encrypted Store')
        self.store_name = config['backing_store']
        self.store = None

        self.enc = config.get('master_enctype', 'A256CBC-HS512')
        master_key_file = config.get('master_key')

        if master_key_file is None:
            raise ValueError('Missing "master_key" for Encrypted Store')

        if (not os.path.isfile(master_key_file) and
                config.get('autogen_master_key') == 'true'):
            # XXX https://github.com/latchset/jwcrypto/issues/50
            size = self.key_sizes.get(self.enc, 512)
            key = JWK(generate='oct', size=size)
            with open(master_key_file, 'w') as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(key.export())

        with open(master_key_file) as f:
            data = f.read()
            key = json_decode(data)
            self.mkey = JWK(**key)

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
