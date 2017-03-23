# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
from __future__ import print_function

import os
import shutil
import tempfile
import unittest

from custodia.compat import configparser
from custodia.plugin import CSStoreError
from custodia.store.encgen import EncryptedOverlay
from custodia.store.sqlite import SqliteStore


CONFIG = u"""
[store:teststore]
dburi = ${tmpdir}/teststore.sqlite

[store:enc_noauto]
backing_store = teststore
master_key = ${tmpdir}/master.key

[store:enc_auto]
backing_store = teststore
master_key = ${tmpdir}/master.key
autogen_master_key = true
"""


class EncryptedOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            defaults={'tmpdir': cls.tmpdir}
        )
        cls.parser.read_string(CONFIG)
        cls.backing_store = SqliteStore(cls.parser, 'store:teststore')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir)

    def test_autogen(self):
        master_key = os.path.join(self.tmpdir, 'master.key')
        with self.assertRaises(IOError):
            EncryptedOverlay(self.parser, 'store:enc_noauto')

        self.assertFalse(os.path.isfile(master_key))
        enc = EncryptedOverlay(self.parser, 'store:enc_auto')
        self.assertTrue(os.path.isfile(master_key))
        stats = os.stat(master_key)

        # second attempt does not override master key
        enc = EncryptedOverlay(self.parser, 'store:enc_auto')
        self.assertEqual(stats, os.stat(master_key))

        enc.store = self.backing_store
        enc.set('key', 'value')
        self.assertEqual(enc.get('key'), 'value')
        self.assertNotEqual(enc.store.get('key'), 'value')

        # new master key
        os.unlink(master_key)
        enc2 = EncryptedOverlay(self.parser, 'store:enc_auto')
        enc2.store = self.backing_store
        with self.assertRaises(CSStoreError):
            # different key causes MAC error during decryption
            self.assertEqual(enc2.get('key'), 'value')
