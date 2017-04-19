# Copyright (C) 2017  Custodia project Contributors, for licensee see COPYING
from __future__ import absolute_import

import configparser
import os

import ipalib

import mock

import pytest

from custodia.ipa.vault import FreeIPA, IPAVault, krb5_unparse_principal_name


CONFIG = u"""
[store:ipa_service]
vault_type = service
principal = custodia/ipa.example

[store:ipa_user]
vault_type = user
user = john

[store:ipa_shared]
vault_type = shared

[store:ipa_invalid]
vault_type = invalid

[store:ipa_autodiscover]

[store:ipa_environ]
krb5config = /path/to/krb5.conf
keytab = /path/to/custodia.keytab
ccache = FILE:/path/to/ccache
"""

vault_parametrize = pytest.mark.parametrize(
    'plugin,vault_type,vault_args',
    [
        ('store:ipa_service', 'service', {'service': 'custodia/ipa.example'}),
        ('store:ipa_user', 'user', {'username': 'john'}),
        ('store:ipa_shared', 'shared', {'shared': True}),
    ]
)


class TestCustodiaIPA:
    def setup_method(self, method):
        self.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
        )
        self.parser.read_string(CONFIG)
        # mocked ipalib.api
        self.p_api = mock.patch('ipalib.api', autospec=ipalib.api)
        self.m_api = self.p_api.start()
        self.m_api.isdone.return_value = False
        self.m_api.env = mock.Mock()
        self.m_api.env.server = 'server.ipa.example'
        self.m_api.Backend = mock.Mock()
        self.m_api.Command = mock.Mock()
        self.m_api.Command.ping.return_value = {
            u'summary': u'IPA server version 4.4.3. API version 2.215',
        }
        self.m_api.Command.vaultconfig_show.return_value = {
            u'result': {
                u'kra_server_server': [u'ipa.example'],
            }
        }
        # mocked get_principal
        self.p_get_principal = mock.patch('custodia.ipa.vault.get_principal')
        self.m_get_principal = self.p_get_principal.start()
        self.m_get_principal.return_value = 'custodia/ipa.example@IPA.EXAMPLE'
        # mocked environ (empty dict)
        self.p_env = mock.patch.dict('os.environ', clear=True)
        self.p_env.start()

    def teardown_method(self, method):
        self.p_api.stop()
        self.p_get_principal.stop()
        self.p_env.stop()

    def test_api_init(self):
        m_api = self.m_api
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

        assert os.environ == dict(NSS_STRICT_NOFORK='DISABLED')

    def test_api_environ(self):
        assert os.environ == {}
        IPAVault(self.parser, 'store:ipa_environ')
        assert os.environ == dict(
            NSS_STRICT_NOFORK='DISABLED',
            KRB5_CONFIG='/path/to/krb5.conf',
            KRB5_CLIENT_KTNAME='/path/to/custodia.keytab',
            KRB5CCNAME='FILE:/path/to/ccache',
        )

    def test_invalid_vault_type(self):
        pytest.raises(ValueError, IPAVault, self.parser, 'store:ipa_invalid')

    def test_vault_autodiscover_service(self):
        self.m_get_principal.return_value = 'custodia/ipa.example@IPA.EXAMPLE'
        ipa = IPAVault(self.parser, 'store:ipa_autodiscover')
        assert ipa.vault_type == 'service'
        assert ipa.principal == 'custodia/ipa.example'
        assert ipa.user is None

    def test_vault_autodiscover_user(self):
        self.m_get_principal.return_value = 'john@IPA.EXAMPLE'
        ipa = IPAVault(self.parser, 'store:ipa_autodiscover')
        assert ipa.vault_type == 'user'
        assert ipa.principal is None
        assert ipa.user == 'john'

    @vault_parametrize
    def test_vault_set(self, plugin, vault_type, vault_args):
        ipa = IPAVault(self.parser, plugin)
        assert ipa.vault_type == vault_type
        self.m_api.Command.ping.assert_called_once()
        ipa.set('directory/testkey', 'testvalue')
        self.m_api.Command.vault_add.assert_called_once_with(
            'directory__testkey',
            ipavaulttype=u'standard',
            **vault_args
        )
        self.m_api.Command.vault_archive.assert_called_once_with(
            'directory__testkey',
            data=b'testvalue',
            **vault_args
        )

    @vault_parametrize
    def test_vault_get(self, plugin, vault_type, vault_args):
        ipa = IPAVault(self.parser, plugin)
        assert ipa.vault_type == vault_type
        self.m_api.Command.vault_retrieve.return_value = {
            u'result': {
                u'data': b'testvalue',
            }
        }
        assert ipa.get('directory/testkey') == b'testvalue'
        self.m_api.Command.vault_retrieve.assert_called_once_with(
            'directory__testkey',
            **vault_args
        )

    @vault_parametrize
    def test_vault_list(self, plugin, vault_type, vault_args):
        ipa = IPAVault(self.parser, plugin)
        assert ipa.vault_type == vault_type
        self.m_api.Command.vault_find.return_value = {
            u'result': [{'cn': [u'directory__testkey']}]
        }
        assert ipa.list('directory') == ['testkey']
        self.m_api.Command.vault_find.assert_called_once_with(
            ipavaulttype=u'standard',
            **vault_args
        )

    @vault_parametrize
    def test_vault_cut(self, plugin, vault_type, vault_args):
        ipa = IPAVault(self.parser, plugin)
        assert ipa.vault_type == vault_type
        ipa.cut('directory/testkey')
        self.m_api.Command.vault_del.assert_called_once_with(
            'directory__testkey',
            **vault_args
        )


@pytest.mark.parametrize('principal,result', [
    ('john@IPA.EXAMPLE',
     (None, 'john', 'IPA.EXAMPLE')),
    ('host/host.invalid@IPA.EXAMPLE',
     ('host', 'host.invalid', 'IPA.EXAMPLE')),
    ('custodia/host.invalid@IPA.EXAMPLE',
     ('custodia', 'host.invalid', 'IPA.EXAMPLE')),
    ('whatever/custodia/host.invalid@IPA.EXAMPLE',
     ('whatever/custodia', 'host.invalid', 'IPA.EXAMPLE')),
])
def test_unparse(principal, result):
    assert krb5_unparse_principal_name(principal) == result
