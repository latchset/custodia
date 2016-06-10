# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
from __future__ import print_function

import os
import unittest

from custodia.store.interface import CSStoreExists
from custodia.store.sqlite import SqliteStore


class SqliteStoreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = SqliteStore({'dburi': 'testdbstore.sqlite'})

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink('testdbstore.sqlite')
        except OSError:
            pass

    def test_0_get_empty(self):
        value = self.store.get('test')
        self.assertEqual(value, None)

    def test_1_list_none(self):
        value = self.store.list('test')
        self.assertEqual(value, None)

    def test_2_set_key(self):
        self.store.set('key', 'value')
        value = self.store.get('key')
        self.assertEqual(value, 'value')

    def test_3_list_key(self):
        value = self.store.list()
        self.assertEqual(value, ['key'])

        value = self.store.list('k')
        self.assertEqual(value, None)

    def test_4_multiple_keys(self):
        self.store.set('/sub1/key1', 'value11')
        self.store.set('/sub1/key2', 'value12')
        self.store.set('/sub1/key3', 'value13')
        self.store.set('/sub2/key1', 'value21')
        self.store.set('/sub2/key2', 'value22')
        self.store.set('/oth3/key1', 'value31')

        value = self.store.list()
        self.assertEqual(value,
                         sorted(['key',
                                 'sub1/key1', 'sub1/key2',
                                 'sub1/key3', 'sub2/key1',
                                 'sub2/key2', 'oth3/key1']))

        value = self.store.list('/sub')
        self.assertEqual(value, None)

        value = self.store.list('/sub2')
        self.assertEqual(value, sorted(['key1', 'key2']))

        self.store.set('/x', '')
        value = self.store.list('/x')
        self.assertEqual(value, [])

        value = self.store.list('/sub1/key1/')
        self.assertEqual(value, [])

        value = self.store.get('/sub1')
        self.assertEqual(value, None)

        value = self.store.get('/sub2/key1')
        self.assertEqual(value, 'value21')

        value = self.store.get('/sub%')
        self.assertEqual(value, None)

    def test_5_set_replace(self):
        with self.assertRaises(CSStoreExists):
            self.store.set('key', 'replaced')

        self.store.set('key', 'replaced', replace=True)

        value = self.store.get('key')
        self.assertEqual(value, 'replaced')

    def test_6_cut_1(self):
        self.store.set('keycut', 'value')
        ret = self.store.cut('keycut')
        self.assertEqual(ret, True)
        value = self.store.get('keycut')
        self.assertEqual(value, None)

    def test_6_cut_2_empty(self):
        ret = self.store.cut('keycut')
        self.assertEqual(ret, False)

    def test_7_span_1(self):
        self.store.span('/span')
        value = self.store.list('/span')
        self.assertEqual(value, [])

    def test_7_span_2(self):
        self.store.span('/span/2')
        self.store.span('/span/2/span')
        value = self.store.list('/span')
        self.assertEqual(value, ['2', '2/span'])
        value = self.store.list('/span/2')
        self.assertEqual(value, ['span'])
        value = self.store.list('/span/2/span')
        self.assertEqual(value, [])

    def test_8_cut_span(self):
        ret = self.store.cut('/span/2')
        self.assertEqual(ret, True)
