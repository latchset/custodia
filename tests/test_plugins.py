# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

import unittest

import pkg_resources

from custodia.client import CustodiaHTTPClient
from custodia.httpd.authenticators import HTTPAuthenticator
from custodia.httpd.authorizers import HTTPAuthorizer
from custodia.store.interface import CSStore


class TestCustodiaPlugins(unittest.TestCase):
    project_name = 'custodia'

    def get_entry_points(self, group):
        eps = []
        for e in pkg_resources.iter_entry_points(group):
            if e.dist.project_name != self.project_name:
                # only interested in our own entry points
                continue
            eps.append(e)
        return eps

    def assert_ep(self, ep, basecls):
        try:
            cls = ep.resolve()
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
