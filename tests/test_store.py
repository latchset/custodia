# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
from __future__ import print_function

import os
import shutil
import tempfile
import unittest

from custodia.store.encgen import EncryptedOverlay
from custodia.store.interface import CSStoreError
from custodia.store.sqlite import SqliteStore


class EncryptedOverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.backing_store = SqliteStore(
            {'dburi': os.path.join(self.tmpdir, 'teststore.sqlite')}
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_autogen(self):
        master_key = os.path.join(self.tmpdir, 'master.key')
        with self.assertRaises(IOError):
            EncryptedOverlay({
                'backing_store': 'teststore',
                'master_key': master_key})

        self.assertFalse(os.path.isfile(master_key))
        enc = EncryptedOverlay({
            'backing_store': 'teststore',
            'master_key': master_key,
            'autogen_master_key': 'true'
        })
        self.assertTrue(os.path.isfile(master_key))
        stats = os.stat(master_key)

        # second attempt does not override master key
        enc = EncryptedOverlay({
            'backing_store': 'teststore',
            'master_key': master_key,
            'autogen_master_key': 'true'
        })
        self.assertEqual(stats, os.stat(master_key))

        enc.store = self.backing_store
        enc.set('key', 'value')
        self.assertEqual(enc.get('key'), 'value')
        self.assertNotEqual(enc.store.get('key'), 'value')

        # new master key
        os.unlink(master_key)
        enc2 = EncryptedOverlay({
            'backing_store': 'teststore',
            'master_key': master_key,
            'autogen_master_key': 'true'
        })
        enc2.store = self.backing_store
        with self.assertRaises(CSStoreError):
            # different key causes MAC error during decryption
            self.assertEqual(enc2.get('key'), 'value')
