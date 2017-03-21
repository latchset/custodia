# Copyright (C) 2017  Custodia project Contributors, for licensee see COPYING

import configparser
import unittest

import ipalib

import mock

from custodia.ipa.vault import FreeIPA, IPAVault


CONFIG = u"""
[store:ipa]
principal = custodia/ipa.example
"""


class TestCustodiaIPA(unittest.TestCase):
    def setUp(self):
        self.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
        )
        self.parser.read_string(CONFIG)
        self.p_api = mock.patch('ipalib.api', autospec=ipalib.api)
        self.m_api = self.p_api.start()
        self.m_api.Backend = mock.Mock()
        self.m_api.Command = mock.Mock()
        self.m_api.Command.vaultconfig_show.return_value = {
            u'result': {
                u'kra_server_server': [u'ipa.example'],
            }
        }

    def tearDown(self):
        self.p_api.stop()

    def test_api_init(self):
        m_api = self.m_api
        m_api.isdone.return_value = False
        freeipa = FreeIPA(api=m_api)
        m_api.isdone.assert_called_once_with('bootstrap')
        m_api.bootstrap.assert_called_once_with(
            context='cli',
            debug=False,
            log=None,
        )

        m_api.Backend.rpcclient.isconnected.return_value = False
        with freeipa:
            m_api.Backend.rpcclient.connect.assert_called_once()
            m_api.Backend.rpcclient.isconnected.return_value = True
        m_api.Backend.rpcclient.disconnect.assert_called_once()

    def test_vault_set(self):
        ipa = IPAVault(self.parser, 'store:ipa')
        self.m_api.Command.ping.assert_called_once()
        ipa.set('directory/testkey', 'testvalue')
        self.m_api.Command.vault_add.assert_called_once_with(
            'directory__testkey',
            service=u'custodia/ipa.example',
            ipavaulttype=u'standard',
        )
        self.m_api.Command.vault_archive.assert_called_once_with(
            'directory__testkey',
            data=b'testvalue',
            service=u'custodia/ipa.example'
        )

    def test_vault_get(self):
        ipa = IPAVault(self.parser, 'store:ipa')
        self.m_api.Command.vault_retrieve.return_value = {
            u'result': {
                u'data': b'testvalue',
            }
        }
        self.assertEqual(ipa.get('directory/testkey'), b'testvalue')
        self.m_api.Command.vault_retrieve.assert_called_once_with(
            'directory__testkey',
            service=u'custodia/ipa.example'
        )

    def test_vault_list(self):
        ipa = IPAVault(self.parser, 'store:ipa')
        self.m_api.Command.vault_find.return_value = {
            u'result': [{'cn': [u'directory__testkey']}]
        }
        self.assertEqual(ipa.list('directory'), ['testkey'])
        self.m_api.Command.vault_find.assert_called_once_with(
            ipavaulttype=u'standard',
            service=u'custodia/ipa.example'
        )

    def test_vault_cut(self):
        ipa = IPAVault(self.parser, 'store:ipa')
        ipa.cut('directory/testkey')
        self.m_api.Command.vault_del.assert_called_once_with(
            'directory__testkey',
            service=u'custodia/ipa.example'
        )
