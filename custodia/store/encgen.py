# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os

from jwcrypto.common import json_decode, json_encode
from jwcrypto.jwe import JWE
from jwcrypto.jwk import JWK

from custodia.plugin import CSStore, CSStoreError
from custodia.plugin import PluginOption, REQUIRED


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

    backing_store = PluginOption(str, REQUIRED, None)
    master_enctype = PluginOption(str, 'A256CBC-HS512', None)
    master_key = PluginOption(str, REQUIRED, None)
    autogen_master_key = PluginOption(bool, False, None)

    def __init__(self, config, section):
        super(EncryptedOverlay, self).__init__(config, section)
        self.store_name = self.backing_store
        self.store = None

        if (not os.path.isfile(self.master_key) and
                self.autogen_master_key):
            # XXX https://github.com/latchset/jwcrypto/issues/50
            size = self.key_sizes.get(self.master_enctype, 512)
            key = JWK(generate='oct', size=size)
            with open(self.master_key, 'w') as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(key.export())

        with open(self.master_key) as f:
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
        protected = json_encode({'alg': 'dir', 'enc': self.master_enctype})
        jwe = JWE(value, protected)
        jwe.add_recipient(self.mkey)
        cvalue = jwe.serialize(compact=True)
        return self.store.set(key, cvalue, replace)

    def span(self, key):
        return self.store.span(key)

    def list(self, keyfilter=''):
        return self.store.list(keyfilter)

    def cut(self, key):
        return self.store.cut(key)
