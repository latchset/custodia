# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import grp
import os
import pwd
import unittest

from custodia.httpd import authenticators


class TestAuthenticators(unittest.TestCase):
    def test_cred(self):
        # pylint: disable=protected-access
        cred = authenticators.SimpleCredsAuth({})
        self.assertEqual(cred._uid, 0)
        self.assertEqual(cred._gid, 0)

        cred = authenticators.SimpleCredsAuth({'uid': '0', 'gid': '0'})
        self.assertEqual(cred._uid, 0)
        self.assertEqual(cred._gid, 0)

        cred = authenticators.SimpleCredsAuth({'uid': 'root', 'gid': 'root'})
        self.assertEqual(cred._uid, 0)
        self.assertEqual(cred._gid, 0)

        user = pwd.getpwuid(os.getuid())
        group = grp.getgrgid(user.pw_gid)

        cred = authenticators.SimpleCredsAuth(
            {'uid': user.pw_name, 'gid': group.gr_name})
        self.assertNotEqual(cred._uid, 0)
        self.assertEqual(cred._uid, user.pw_uid)
        self.assertNotEqual(cred._gid, 0)
        self.assertEqual(cred._gid, group.gr_gid)
