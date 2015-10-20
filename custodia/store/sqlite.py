# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import print_function

import logging
import os
import sqlite3
import unittest

from custodia.store.interface import CSStore, CSStoreError, CSStoreExists


logger = logging.getLogger(__name__)


class SqliteStore(CSStore):

    def __init__(self, config):
        if 'dburi' not in config:
            raise ValueError('Missing "dburi" for Sqlite Store')
        self.dburi = config['dburi']
        if 'table' in config:
            self.table = config['table']
        else:
            self.table = "CustodiaSecrets"

        # Initialize the DB by trying to create the default table
        try:
            conn = sqlite3.connect(self.dburi)
            with conn:
                c = conn.cursor()
                self._create(c)
        except sqlite3.Error:
            logger.exception("Error creating table %s", self.table)
            raise CSStoreError('Error occurred while trying to init db')

    def get(self, key):
        logger.debug("Fetching key %s", key)
        query = "SELECT value from %s WHERE key=?" % self.table
        try:
            conn = sqlite3.connect(self.dburi)
            c = conn.cursor()
            r = c.execute(query, (key,))
            value = r.fetchall()
        except sqlite3.Error:
            logger.exception("Error fetching key %s", key)
            raise CSStoreError('Error occurred while trying to get key')
        logger.debug("Fetched key %s got result: %r", key, value)
        if len(value) > 0:
            return value[0][0]
        else:
            return None

    def _create(self, cur):
        create = "CREATE TABLE IF NOT EXISTS %s " \
                 "(key PRIMARY KEY UNIQUE, value)" % self.table
        cur.execute(create)

    def set(self, key, value, replace=False):
        logger.debug("Setting key %s to value %s (replace=%s)", key, value,
                     replace)
        if key.endswith('/'):
            raise ValueError('Invalid Key name, cannot end in "/"')
        if replace:
            query = "INSERT OR REPLACE into %s VALUES (?, ?)"
        else:
            query = "INSERT into %s VALUES (?, ?)"
        setdata = query % (self.table,)
        try:
            conn = sqlite3.connect(self.dburi)
            with conn:
                c = conn.cursor()
                self._create(c)
                c.execute(setdata, (key, value))
        except sqlite3.IntegrityError as err:
            raise CSStoreExists(str(err))
        except sqlite3.Error as err:
            logger.exception("Error storing key %s", key)
            raise CSStoreError('Error occurred while trying to store key')

    def span(self, key):
        name = key.rstrip('/')
        logger.debug("Creating container %s", name)
        query = "INSERT into %s VALUES (?, '')"
        setdata = query % (self.table,)
        try:
            conn = sqlite3.connect(self.dburi)
            with conn:
                c = conn.cursor()
                self._create(c)
                c.execute(setdata, (name,))
        except sqlite3.IntegrityError as err:
            raise CSStoreExists(str(err))
        except sqlite3.Error:
            logger.exception("Error creating key %s", name)
            raise CSStoreError('Error occurred while trying to span container')

    def list(self, keyfilter=''):
        path = keyfilter.rstrip('/')
        logger.debug("Listing keys matching %s", path)
        child_prefix = path if path == '' else path + '/'
        search = "SELECT key FROM %s WHERE key LIKE ?" % self.table
        key = "%s%%" % (path,)
        try:
            conn = sqlite3.connect(self.dburi)
            r = conn.execute(search, (key,))
            rows = r.fetchall()
        except sqlite3.Error:
            logger.exception("Error listing %s: [%r]", keyfilter)
            raise CSStoreError('Error occurred while trying to list keys')
        logger.debug("Searched for %s got result: %r", path, rows)
        if len(rows) > 0:
            parent_exists = False
            value = list()
            for row in rows:
                if row[0] == path or row[0] == child_prefix:
                    parent_exists = True
                    continue
                if not row[0].startswith(child_prefix):
                    continue
                value.append(row[0][len(child_prefix):].lstrip('/'))

            if value:
                logger.debug("Returning sorted values %r", value)
                return sorted(value)
            elif parent_exists:
                logger.debug("Returning empty list")
                return []
        elif keyfilter == '':
            logger.debug("Returning empty list")
            return []
        logger.debug("Returning 'Not Found'")
        return None

    def cut(self, key):
        logger.debug("Removing key %s", key)
        query = "DELETE from %s WHERE key=?" % self.table
        try:
            conn = sqlite3.connect(self.dburi)
            with conn:
                c = conn.cursor()
                r = c.execute(query, (key,))
        except sqlite3.Error:
            logger.error("Error removing key %s", key)
            raise CSStoreError('Error occurred while trying to cut key')
        logger.debug("Key %s %s", key,
                     "removed" if r.rowcount > 0 else "not found")
        if r.rowcount > 0:
            return True
        return False


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
