# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import unittest

import pkg_resources

from custodia.client import CustodiaHTTPClient
from custodia.plugin import CSStore, HTTPAuthenticator, HTTPAuthorizer

try:
    # pylint: disable=unused-import
    import ipaclient  # noqa: F401
except ImportError:
    HAS_IPA = False
else:
    HAS_IPA = True


class TestCustodiaPlugins(unittest.TestCase):
    project_name = 'custodia'

    def get_entry_points(self, group):
        eps = []
        for e in pkg_resources.iter_entry_points(group):
            if e.dist.project_name != self.project_name:
                # only interested in our own entry points
                continue
            if not HAS_IPA and e.module_name.startswith('custodia.ipa'):
                # skip IPA plugins when ipaclient isn't installed
                continue
            eps.append(e)
        return eps

    def assert_ep(self, ep, basecls):
        try:
            # backwards compatibility with old setuptools
            if hasattr(ep, "resolve"):
                cls = ep.resolve()
            else:
                cls = ep.load(require=False)
        except Exception as e:  # pylint: disable=broad-except
            self.fail("Failed to load %r: %r" % (ep, e))
        if not issubclass(cls, basecls):
            self.fail("%r is not a subclass of %r" % (cls, basecls))

    def test_authenticators(self):
        for ep in self.get_entry_points('custodia.authenticators'):
            self.assert_ep(ep, HTTPAuthenticator)

    def test_authorizers(self):
        for ep in self.get_entry_points('custodia.authorizers'):
            self.assert_ep(ep, HTTPAuthorizer)

    def test_clients(self):
        for ep in self.get_entry_points('custodia.clients'):
            self.assert_ep(ep, CustodiaHTTPClient)

    def test_stores(self):
        for ep in self.get_entry_points('custodia.stores'):
            self.assert_ep(ep, CSStore)
