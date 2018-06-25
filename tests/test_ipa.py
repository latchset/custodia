# Copyright (C) 2017  Custodia project Contributors, for licensee see COPYING
from __future__ import absolute_import

import base64
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

import pkg_resources

import pytest

from custodia.compat import configparser

try:
    import ipaclient.plugins.vault
    import ipalib
except ImportError:
    HAS_IPA = False
    NotFound = None
    IPACertRequest = None
    IPAInterface = IPA_SECTIONNAME = None
    IPAVault = krb5_unparse_principal_name = None
else:
    HAS_IPA = True
    from ipalib.errors import NotFound
    from custodia.ipa.certrequest import IPACertRequest
    from custodia.ipa.interface import IPAInterface, IPA_SECTIONNAME
    from custodia.ipa.vault import IPAVault, krb5_unparse_principal_name

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None


CONFIG = u"""
[DEFAULT]
rundir = /tmp/invalid

[store:ipa_service]
handler = IPAVault
vault_type = service
principal = custodia/ipa.example

[store:ipa_user]
handler = IPAVault
vault_type = user
user = john

[store:ipa_shared]
handler = IPAVault
vault_type = shared

[store:ipa_invalid]
handler = IPAVault
vault_type = invalid

[store:ipa_autodiscover]
handler = IPAVault

[store:certreq]
handler = IPACertRequest
backing_store = ipa_service

[auth:ipa]
handler = IPAInterface
krb5config = /path/to/krb5.conf
keytab = /path/to/custodia.keytab
ccache = FILE:/path/to/ccache
"""

RSA_KEY = b"""
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAvHLiqvX6NCV6iZtquXmqu0AlyfDmcoNK2d27dsWZVfPekvGH
T95RYASD+ly+kwzvtKBIZQHsPOaYpQjzOfpzCOwUWZcHjj4g8/fp99MdhMyWzXY0
U8mytZND7ZP2LW2kmkdP2G8Euw2TB2hCbWguVyI3pNXbsLxzquR8Xr/AbM8VJBTO
Qd/8tXen3GoXpYvDY2PQs1MQQy4yKpeVj/j146hCh+Ahw4sO5yLk+FXjZ+ZfSBnh
2uBjHqDG+EbvLLDJ2DRFO6cMPPjK3Q4evWOQzl6kwN2uwGfLWPRiYZ1KwcdUieHA
eKTYb8Yc832bc7CsHlEQpvKohTv5vyVb2RTsTwIDAQABAoIBAQCdPovOtbNSIdfO
zOVP4KrK1mrxx1azRMSHaJKNN7KL2xLksC8FQO/L29i4Zv0KPOgjYv8lcWZLJutG
AmLaBRZJ4pvUacZ/NW5PxJTxGrLt5b0Lsk9Vft7kzf4HVsg6/ds0dL62TWS4JEqE
CsYq/px0TnP50g0fuxAVD9SLRxtsbiyDbYUxcsVrPA9KHmLdRaebhw44IeBqvY9d
Tl+SxzBtyah8N8rlzQIo/O3P+HHx4CvBBXfGNO4tAXM9DgWHgTiBMku6X4OeXikQ
cNfPygvUF8Npt4ZpvqFlUWSzkU/+vfBQKzd0m9PLNV0SVe743EucrmDWFpHGbwns
TgHfRtqhAoGBAOCwlpnVyJ8NHrxR53VBQE+M3VgLrxtzRjQR21K7XAlBpLNs3+c0
dGE2seY/HFaXEwrmQNFNEAo2OKTYkBrtI82h6/93vq4OFlVZCxABlw9PJ0LZfL9P
8HMdM5oaldMc1NsDD8lc/M2PAhFTni9zmvmzEdCWO/hlJHH876GSjiBxAoGBANa1
dmcZGuMIu/c9KpsvIEp7ZknFKlKdQQlB8lTPl0vgC9DN4QDo8WfbgTi2Q9Xcs5ni
qx9uzlGHwwx9LR6b8D+nhngpX/2beD8T+me8vY9gYwdvMci5JhNdwAO2T0Ry4V+a
/8AthOb/+cWjvoPitT6nXXdLM1po4hmt+jVCEji/AoGAM4arcqnA8SB8HOmXb59A
FT4TgF5lkKD1x3kU17sZlxHTqEXebtHromN9lnSAlibc+hHlaVoHxJ+8i6kSGuqo
3D42tYYLVzTp0Da0P75tmtgnA8CGSAUX+f4HWF6iXyBse7EPDLljS+xwp/KKAw26
y2pSOohJRmRDYFSFy4KlTzECgYBPqaxwvEPZkNgM98jjIy0b9YUSQfFeDbKfuLQs
+4jrQgmgQ4MET2miWzMq05V/uA97PTq4wugSIAkijR88iCcvtvyRgOh4tEJ9RPBX
pRPAKscTbxJNo0SZUuN3fSEUCHvOeTgDGeCBxN/rkMGTNX6B7J8lL+Wx2dBqLr7z
G7yfCQKBgQDWHff2GHJaSyEY6N8tfU7bVbhcBFuBGdxaPSBiA1PYHJWjyI7TI5ma
v7cR0gAfhieZtwQuRJUjgB2ZbQXfmiLEJpyENxiNS2Sc/QfddzlprMZb2gcTenG1
z6KdW9BiwDOdQhy5vCL09uuR/CZle47TvOdgIn7N4HcGzbUNRnEQ+A==
-----END RSA PRIVATE KEY-----
"""

CERT_PEM = b"""
Issuer: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Subject: organizationName=IPA.EXAMPLE, commonName=client1.ipa.example
Serial Number: 43
Validity:
    Not Before: 2017-04-12 10:10:12
    Not After: 2019-04-13 10:10:12
-----BEGIN CERTIFICATE-----
MIIEMTCCAxmgAwIBAgIBKzANBgkqhkiG9w0BAQsFADA2MRQwEgYDVQQKDAtJUEEu
RVhBTVBMRTEeMBwGA1UEAwwVQ2VydGlmaWNhdGUgQXV0aG9yaXR5MB4XDTE3MDQx
MjEwMTAxMloXDTE5MDQxMzEwMTAxMlowNDEUMBIGA1UECgwLSVBBLkVYQU1QTEUx
HDAaBgNVBAMME2NsaWVudDEuaXBhLmV4YW1wbGUwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQC8cuKq9fo0JXqJm2q5eaq7QCXJ8OZyg0rZ3bt2xZlV896S
8YdP3lFgBIP6XL6TDO+0oEhlAew85pilCPM5+nMI7BRZlweOPiDz9+n30x2EzJbN
djRTybK1k0Ptk/YtbaSaR0/YbwS7DZMHaEJtaC5XIjek1duwvHOq5Hxev8BszxUk
FM5B3/y1d6fcaheli8NjY9CzUxBDLjIql5WP+PXjqEKH4CHDiw7nIuT4VeNn5l9I
GeHa4GMeoMb4Ru8ssMnYNEU7pww8+MrdDh69Y5DOXqTA3a7AZ8tY9GJhnUrBx1SJ
4cB4pNhvxhzzfZtzsKweURCm8qiFO/m/JVvZFOxPAgMBAAGjggFKMIIBRjAfBgNV
HSMEGDAWgBQtd7FcS4X0qxR58HZPpjkAQRMNKDA9BggrBgEFBQcBAQQxMC8wLQYI
KwYBBQUHMAGGIWh0dHA6Ly9pcGEtY2EuaXBhLmV4YW1wbGUvY2Evb2NzcDAOBgNV
HQ8BAf8EBAMCBPAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMHYGA1Ud
HwRvMG0wa6AzoDGGL2h0dHA6Ly9pcGEtY2EuaXBhLmV4YW1wbGUvaXBhL2NybC9N
YXN0ZXJDUkwuYmluojSkMjAwMQ4wDAYDVQQKDAVpcGFjYTEeMBwGA1UEAwwVQ2Vy
dGlmaWNhdGUgQXV0aG9yaXR5MB0GA1UdDgQWBBRhaPmYwf/s6nCwIDSnnZDi/Fpv
jzAeBgNVHREEFzAVghNjbGllbnQxLmlwYS5leGFtcGxlMA0GCSqGSIb3DQEBCwUA
A4IBAQChdJscTm+7ceiV4sieKWoZnZxFBEdipv1qErQUcmp3mEGKWrwksOdHt4vs
iYC5o8ITztEFnmGOEiqUJtG+kPF1/E2YyeAZz/Jshm2tTNfc0lFcXo5yh6YaWxkS
Ld9RLUstjx6nEDoRp94Xiv6oA7amXaqxUYF+IFTywCS8ydqjw4YarIcTOYaNgnpB
XS28/NgMWwRMen6TsKheo31b0ZWZhj5OhdjYGc4r8eoZqYNw7FdJLFRCygCxSUdr
B6PZz8xdp5VVPhmhhMVMuBsiflOU5zVQ4G8WDeWq7UTIceZ30nLvD80pFwYXQr0A
AgUFtdTv7EX25GAVtJtXPgfWkaQQ
-----END CERTIFICATE-----
"""

CA_PEM = b"""
Issuer: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Subject: organizationName=IPA.EXAMPLE, commonName=Certificate Authority
Serial Number: 1
Validity:
    Not Before: 2017-04-05 07:56:09
    Not After: 2037-04-05 07:56:09
-----BEGIN CERTIFICATE-----
MIIDizCCAnOgAwIBAgIBATANBgkqhkiG9w0BAQsFADA2MRQwEgYDVQQKDAtJUEEu
RVhBTVBMRTEeMBwGA1UEAwwVQ2VydGlmaWNhdGUgQXV0aG9yaXR5MB4XDTE3MDQw
NTA3NTYwOVoXDTM3MDQwNTA3NTYwOVowNjEUMBIGA1UECgwLSVBBLkVYQU1QTEUx
HjAcBgNVBAMMFUNlcnRpZmljYXRlIEF1dGhvcml0eTCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAKuWxKJzcBM34GuCO02Z4xxqWTZydFn6G9Kyfu86rqxf
+i9lXQXa5/GnbSiK13XSVaakd5WlbPmcPmzIQy33WFgr2uKXEYBXgia6zZVIwsh5
fhlSwN+WCNBykyyC83s73FV8QVuGE0sZnCPt+H7zAFrcC2oyLopsQf+twzVEuZGr
ONDalSxdHdXUYnB1nIlNuDdwb3e9zOHcdqhwN3HMqoNrjIWx7qa2wvf6KcHCoLrK
VnlEqbk/9llDeXf03NatEyqfa08GlDoHgqqrROMK0vAbmz+nGv9YFHLuX344ZJ58
zIBbrp/sUzWThKyXlN6U8t6Wdkx3/TAyORVr8cq6YgcCAwEAAaOBozCBoDAfBgNV
HSMEGDAWgBQtd7FcS4X0qxR58HZPpjkAQRMNKDAPBgNVHRMBAf8EBTADAQH/MA4G
A1UdDwEB/wQEAwIBxjAdBgNVHQ4EFgQULXexXEuF9KsUefB2T6Y5AEETDSgwPQYI
KwYBBQUHAQEEMTAvMC0GCCsGAQUFBzABhiFodHRwOi8vaXBhLWNhLmlwYS5leGFt
cGxlL2NhL29jc3AwDQYJKoZIhvcNAQELBQADggEBAKgm8hNI8pgEUY3muAyqO6HO
iBPH3OEljWBNsHNqf9RYSXq148xIbX1X6clSPY4cKyQPzJtkBnesoU+ybuFH/oDV
w+9M51my5zCR0GmHMGW1xbgeKqSEINBXTUy5af2AEzIcOlI5d1o+OBTpxGLZp+Mt
KuE+T9jdkajHIOK3sk1d7BoHaXcwt/SOev2jPpTJpHZ8bEB/msGB4O+p5sMc4Xot
sGeWEV2/0AtqxhuRxao87NNAqLvP1+UmCq2Rx9fFh2DH4+cuAl+/HU1/mFharzTr
K3quV1cduocb2y4lwLF0I6aRqe73pzLnTvoUjnhutYoCMjKT0ebFPZIHbVgYPTI=
-----END CERTIFICATE-----
"""

vault_parametrize = pytest.mark.parametrize(
    'plugin,vault_type,vault_args',
    [
        ('store:ipa_service', 'service', {'service': 'custodia/ipa.example'}),
        ('store:ipa_user', 'user', {'username': 'john'}),
        ('store:ipa_shared', 'shared', {'shared': True}),
    ]
)


@pytest.mark.skipif(mock is None, reason='requires mock')
@pytest.mark.skipif(not HAS_IPA, reason='requires ipaclient package')
class BaseTest(object):
    def setup_method(self, method):
        # pylint: disable=attribute-defined-outside-init
        self.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
        )
        self.parser.read_string(CONFIG)
        # config
        self.config = {
            'debug': False,
            'authenticators': {},
            'stores': {},
        }
        # mocked ipalib.api
        self.p_api = mock.patch('ipalib.api', autospec=ipalib.api)
        self.m_api = self.p_api.start()
        self.m_api.isdone.return_value = False
        self.m_api.env = mock.Mock()
        self.m_api.env.server = 'server.ipa.example'
        self.m_api.env.realm = u'IPA.EXAMPLE'
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
        self.p_get_principal = mock.patch(
            'custodia.ipa.interface.get_principal')
        self.m_get_principal = self.p_get_principal.start()
        self.m_get_principal.return_value = None
        # mocked environ (empty dict)
        self.p_env = mock.patch.dict('os.environ', clear=True)
        self.p_env.start()

    def teardown_method(self, method):
        self.p_api.stop()
        self.p_get_principal.stop()
        self.p_env.stop()


class TestCustodiaIPA(BaseTest):

    def test_api_init(self):
        os.environ.pop('PYTEST_CURRENT_TEST', None)
        assert os.environ == {}
        m_api = self.m_api
        ipa = IPAInterface(
            self.parser,
            IPA_SECTIONNAME,
            api=m_api
        )
        self.config['authenticators']['ipa'] = ipa
        ipa.finalize_init(self.config, self.parser, None)
        assert (self.config['authenticators']['ipa'] is
                IPAInterface.from_config(self.config))

        m_api.isdone.assert_called_once_with('bootstrap')
        m_api.bootstrap.assert_called_once_with(
            context='cli',
            debug=False,
            dot_ipa=u'/tmp/invalid',
            home=u'/tmp/invalid',
            log=None,
        )

        m_api.Backend.rpcclient.isconnected.return_value = False
        with ipa:
            m_api.Backend.rpcclient.connect.assert_any_call()
            m_api.Backend.rpcclient.isconnected.return_value = True
        m_api.Backend.rpcclient.disconnect.assert_any_call()

        assert os.environ == dict(
            NSS_STRICT_NOFORK='DISABLED',
            KRB5_CONFIG='/path/to/krb5.conf',
            KRB5_CLIENT_KTNAME='/path/to/custodia.keytab',
            KRB5CCNAME='FILE:/path/to/ccache',
        )
        assert ipaclient.plugins.vault.USER_CACHE_PATH == '/tmp/invalid'


class TestCustodiaIPAVault(BaseTest):
    def mkinstance(self, principal, section):
        self.m_get_principal.return_value = principal

        ipa = IPAInterface(self.parser, IPA_SECTIONNAME)
        self.config['authenticators']['ipa'] = ipa
        ipa.finalize_init(self.config, self.parser, None)
        assert (self.config['authenticators']['ipa'] is
                IPAInterface.from_config(self.config))

        vault = IPAVault(self.parser, section)
        self.config['stores'][section] = vault
        vault.finalize_init(self.config, self.parser, None)
        return vault

    def test_invalid_vault_type(self):
        pytest.raises(
            ValueError,
            self.mkinstance,
            'custodia/ipa.example@IPA.EXAMPLE',
            'store:ipa_invalid'
        )

    def test_vault_autodiscover_service(self):
        ipa = self.mkinstance('custodia/ipa.example@IPA.EXAMPLE',
                              'store:ipa_autodiscover')
        assert ipa.vault_type == 'service'
        assert ipa.principal == 'custodia/ipa.example'
        assert ipa.user is None

    def test_vault_autodiscover_user(self):
        ipa = self.mkinstance('john@IPA.EXAMPLE', 'store:ipa_autodiscover')
        assert ipa.vault_type == 'user'
        assert ipa.principal is None
        assert ipa.user == 'john'

    @vault_parametrize
    def test_vault_set(self, plugin, vault_type, vault_args):
        ipa = self.mkinstance('john@IPA.EXAMPLE', plugin)
        assert ipa.vault_type == vault_type
        self.m_api.Command.ping.assert_called_once_with()
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
        ipa = self.mkinstance('custodia/ipa.example@IPA.EXAMPLE', plugin)
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
        ipa = self.mkinstance('custodia/ipa.example@IPA.EXAMPLE', plugin)
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
        ipa = self.mkinstance('custodia/ipa.example@IPA.EXAMPLE', plugin)
        assert ipa.vault_type == vault_type
        ipa.cut('directory/testkey')
        self.m_api.Command.vault_del.assert_called_once_with(
            'directory__testkey',
            **vault_args
        )


class TestCustodiaIPACertRequests(BaseTest):
    def setup_method(self, method):
        super(TestCustodiaIPACertRequests, self).setup_method(method)
        cert = x509.load_pem_x509_certificate(CERT_PEM, default_backend())
        cert_der = cert.public_bytes(serialization.Encoding.DER)
        cert_stripped = base64.b64encode(cert_der)
        ca = x509.load_pem_x509_certificate(CA_PEM, default_backend())
        ca_der = ca.public_bytes(serialization.Encoding.DER)
        self.m_api.Command.cert_request.return_value = {
            u'result': {
                u'subject': 'dummy subject',
                u'request_id': 1,
                u'serial_number': 1,
                u'certificate': cert_stripped,
                u'certificate_chain': (
                    cert_der,
                    ca_der,
                )
            }
        }

    def mkinstance(self, principal, section):
        self.m_get_principal.return_value = principal

        ipa = IPAInterface(self.parser, IPA_SECTIONNAME)
        self.config['authenticators']['ipa'] = ipa
        ipa.finalize_init(self.config, self.parser, None)
        assert (self.config['authenticators']['ipa'] is
                IPAInterface.from_config(self.config))

        certreq = IPACertRequest(self.parser, section)
        self.config['stores'][section] = certreq
        storename = certreq.backing_store
        storesection = u'store:{0}'.format(storename)

        vault = IPAVault(self.parser, storesection)
        self.config['stores'][storename] = vault
        vault.finalize_init(self.config, self.parser, None)

        # finalize last
        certreq.finalize_init(self.config, self.parser, None)
        return certreq

    def test_get(self):
        certreq = self.mkinstance(
            'custodia/ipa.example@IPA.EXAMPLE', 'store:certreq')
        self.m_api.Command.vault_retrieve.side_effect = NotFound(reason=u'')
        certreq.get('keys/HTTP/client1.ipa.example')


@pytest.mark.skipif(not HAS_IPA, reason='requires ipaclient package')
@pytest.mark.parametrize('group,name,cls', [
    ('custodia.stores', 'IPAVault', IPAVault),
    ('custodia.stores', 'IPACertRequest', IPACertRequest),
    ('custodia.authenticators', 'IPAInterface', IPAInterface),
])
def test_plugins(group, name, cls, dist='custodia'):
    ep = pkg_resources.get_entry_info(dist, group, name)
    assert ep is not None
    assert ep.dist.project_name == dist
    if hasattr(ep, 'resolve'):
        resolved = ep.resolve()
    else:
        resolved = ep.load(require=False)
    assert resolved is cls


@pytest.mark.skipif(not HAS_IPA, reason='requires ipaclient package')
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
