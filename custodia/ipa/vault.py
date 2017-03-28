# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
"""FreeIPA vault store (PoC)
"""
import os

import ipalib
from ipalib.errors import DuplicateEntry, NotFound
from ipalib.krb_utils import get_principal

import six

from custodia.plugin import CSStore, CSStoreError, CSStoreExists, PluginOption


def krb5_unparse_principal_name(name):
    """Split a Kerberos principal name into parts

    Returns:
       * ('host', hostname, realm) for a host principal
       * (servicename, hostname, realm) for a service principal
       * (None, username, realm) for a user principal

    :param text name: Kerberos principal name
    :return: (service, host, realm) or (None, username, realm)
    """
    prefix, realm = name.split(u'@')
    if u'/' in prefix:
        service, host = prefix.rsplit(u'/', 1)
        return service, host, realm
    else:
        return None, prefix, realm


class FreeIPA(object):
    """FreeIPA wrapper

    Custodia uses a forking server model. We can bootstrap FreeIPA API in
    the main process. Connections must be created in the client process.
    """
    def __init__(self, api=None, ipa_context='cli', ipa_confdir=None,
                 ipa_debug=False):
        if api is None:
            self._api = ipalib.api
        else:
            self._api = api
        self._ipa_config = dict(
            context=ipa_context,
            debug=ipa_debug,
            log=None,  # disable logging to file
        )
        if ipa_confdir is not None:
            self._ipa_config['confdir'] = ipa_confdir
        self._bootstrap()

    @property
    def Command(self):
        return self._api.Command  # pylint: disable=no-member

    @property
    def env(self):
        return self._api.env  # pylint: disable=no-member

    def _bootstrap(self):
        if not self._api.isdone('bootstrap'):
            # TODO: bandaid for "A PKCS #11 module returned CKR_DEVICE_ERROR"
            # https://github.com/avocado-framework/avocado/issues/1112#issuecomment-206999400
            os.environ['NSS_STRICT_NOFORK'] = 'DISABLED'
            self._api.bootstrap(**self._ipa_config)
            self._api.finalize()

    def __enter__(self):
        # pylint: disable=no-member
        if not self._api.Backend.rpcclient.isconnected():
            self._api.Backend.rpcclient.connect()
        # pylint: enable=no-member
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # pylint: disable=no-member
        if self._api.Backend.rpcclient.isconnected():
            self._api.Backend.rpcclient.disconnect()
        # pylint: enable=no-member


class IPAVault(CSStore):
    # vault arguments
    principal = PluginOption(
        str, None,
        "Service principal for service vault (auto-discovered from GSSAPI)"
    )
    user = PluginOption(
        str, None,
        "User name for user vault (auto-discovered from GSSAPI)"
    )
    vault_type = PluginOption(
        str, None,
        "vault type, one of 'user', 'service', 'shared', or "
        "auto-discovered from GSSAPI"
    )

    # Kerberos flags
    krb5config = PluginOption(str, None, "Kerberos krb5.conf override")
    keytab = PluginOption(str, None, "Kerberos keytab for auth")
    ccache = PluginOption(
        str, None, "Kerberos ccache, e,g. FILE:/path/to/ccache")

    # ipalib.api arguments
    ipa_confdir = PluginOption(str, None, "IPA confdir override")
    ipa_context = PluginOption(str, "cli", "IPA bootstrap context")
    ipa_debug = PluginOption(bool, False, "debug mode for ipalib")

    def __init__(self, config, section=None):
        super(IPAVault, self).__init__(config, section)
        # configure Kerberos / GSSAPI and acquire principal
        gssapi_principal = self._gssapi()
        self.logger.info(u"Vault uses Kerberos principal '%s'",
                         gssapi_principal)

        # bootstrap FreeIPA API
        self.ipa = FreeIPA(
            ipa_confdir=self.ipa_confdir,
            ipa_debug=self.ipa_debug,
            ipa_context=self.ipa_context,
        )
        # connect
        with self.ipa:
            self.logger.info("IPA server '%s': %s",
                             self.ipa.env.server,
                             self.ipa.Command.ping()[u'summary'])
            # retrieve and cache KRA transport cert
            response = self.ipa.Command.vaultconfig_show()
            servers = response[u'result'][u'kra_server_server']
            self.logger.info("KRA server(s) %s", ', '.join(servers))

        service, user_host, realm = krb5_unparse_principal_name(
            gssapi_principal)
        self._init_vault_args(service, user_host, realm)

    def _gssapi(self):
        # set client keytab env var for authentication
        if self.keytab is not None:
            os.environ['KRB5_CLIENT_KTNAME'] = self.keytab
        if self.ccache is not None:
            os.environ['KRB5CCNAME'] = self.ccache
        if self.krb5config is not None:
            os.environ['KRB5_CONFIG'] = self.krb5config
        try:
            return get_principal()
        except Exception:
            self.logger.error(
                "Unable to get principal from GSSAPI. Are you missing a "
                "TGT or valid Kerberos keytab?"
            )
            raise

    def _init_vault_args(self, service, user_host, realm):
        if self.vault_type is None:
            self.vault_type = 'user' if service is None else 'service'
            self.logger.info("Setting vault type to '%s' from Kerberos",
                             self.vault_type)

        if self.vault_type == 'shared':
            self._vault_args = {'shared': True}
        elif self.vault_type == 'user':
            if self.user is None:
                if service is not None:
                    msg = "{!r}: User vault requires 'user' parameter"
                    raise ValueError(msg.format(self))
                else:
                    self.user = user_host
                    self.logger.info(u"Setting username '%s' from Kerberos",
                                     self.user)
            if six.PY2 and isinstance(self.user, str):
                self.user = self.user.decode('utf-8')
            self._vault_args = {'username': self.user}
        elif self.vault_type == 'service':
            if self.principal is None:
                if service is None:
                    msg = "{!r}: Service vault requires 'principal' parameter"
                    raise ValueError(msg.format(self))
                else:
                    self.principal = u'/'.join((service, user_host))
                    self.logger.info(u"Setting principal '%s' from Kerberos",
                                     self.principal)
            if six.PY2 and isinstance(self.principal, str):
                self.principal = self.principal.decode('utf-8')
            self._vault_args = {'service': self.principal}
        else:
            msg = '{!r}: Invalid vault type {}'
            raise ValueError(msg.format(self, self.vault_type))

    def _mangle_key(self, key):
        if '__' in key:
            raise ValueError
        key = key.replace('/', '__')
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        return key

    def get(self, key):
        key = self._mangle_key(key)
        with self.ipa as ipa:
            try:
                result = ipa.Command.vault_retrieve(
                    key, **self._vault_args)
            except NotFound as e:
                self.logger.info(str(e))
                return None
            except Exception:
                msg = "Failed to retrieve entry {}".format(key)
                self.logger.exception(msg)
                raise CSStoreError(msg)
            else:
                return result[u'result'][u'data']

    def set(self, key, value, replace=False):
        key = self._mangle_key(key)
        if not isinstance(value, bytes):
            value = value.encode('utf-8')
        with self.ipa as ipa:
            try:
                ipa.Command.vault_add(
                    key, ipavaulttype=u"standard", **self._vault_args)
            except DuplicateEntry:
                if not replace:
                    raise CSStoreExists(key)
            except Exception:
                msg = "Failed to add entry {}".format(key)
                self.logger.exception(msg)
                raise CSStoreError(msg)
            try:
                ipa.Command.vault_archive(
                    key, data=value, **self._vault_args)
            except Exception:
                msg = "Failed to archive entry {}".format(key)
                self.logger.exception(msg)
                raise CSStoreError(msg)

    def span(self, key):
        raise CSStoreError("span is not implemented")

    def list(self, keyfilter=None):
        with self.ipa as ipa:
            try:
                result = ipa.Command.vault_find(
                    ipavaulttype=u"standard", **self._vault_args)
            except Exception:
                msg = "Failed to list entries"
                self.logger.exception(msg)
                raise CSStoreError(msg)

        names = []
        for entry in result[u'result']:
            cn = entry[u'cn'][0]
            key = cn.replace('__', '/')
            if keyfilter is not None and not key.startswith(keyfilter):
                continue
            names.append(key.rsplit('/', 1)[-1])
        return names

    def cut(self, key):
        key = self._mangle_key(key)
        with self.ipa as ipa:
            try:
                ipa.Command.vault_del(key, **self._vault_args)
            except NotFound:
                return False
            except Exception:
                msg = "Failed to delete entry {}".format(key)
                self.logger.exception(msg)
                raise CSStoreError(msg)
            else:
                return True


if __name__ == '__main__':
    from custodia.compat import configparser

    parser = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation()
    )
    parser.read_string(u"""
    [store:ipa_vault]
    """)

    v = IPAVault(parser, "store:ipa_vault")
    v.set('foo', 'bar', replace=True)
    print(v.get('foo'))
    print(v.list())
    v.cut('foo')
    print(v.list())
