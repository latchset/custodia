# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

from __future__ import absolute_import

import grp
import pwd
import unittest

from custodia.compat import configparser
from custodia.httpd import authenticators

CONFIG = u"""
[auth:cred_default]

[auth:cred_int]
uid = 0
gid = 0

[auth:cred_root]
uid = root
gid = root

[auth:cred_user]
uid = root

[auth:cred_group]
gid = root

[auth:cred_other_int]
uid = ${DEFAULT:other_uid}
gid = ${DEFAULT:other_gid}

[auth:cred_other_name]
uid = ${DEFAULT:other_username}
gid = ${DEFAULT:other_groupname}

[auth:header_default]

[auth:header_other]
header = GSSAPI
value =

[auth:header_value]
header = GSSAPI
value = admin

[auth:header_values]
header = GSSAPI
value = admin user
"""


class TestAuthenticators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tests are depending on two existing and distinct users and groups.
        # We chose 'root' with uid/gid 0 and 'nobody', because both exist on
        # all relevant platforms. Tests use a mocked request so they run
        # under any user.
        cls.user = user = pwd.getpwnam('nobody')
        cls.group = group = grp.getgrgid(user.pw_gid)

        cls.parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            defaults={
                'other_uid': str(user.pw_uid),
                'other_username': user.pw_name,
                'other_gid': str(group.gr_gid),
                'other_groupname': group.gr_name,
            }
        )
        cls.parser.read_string(CONFIG)

    def assertCredMatch(self, cred, uid, gid):
        request = {'creds': {'uid': uid, 'gid': gid}, 'client_id': 'tests'}
        self.assertTrue(cred.handle(request))

    def assertCredMismatch(self, cred, uid, gid):
        request = {'creds': {'uid': uid, 'gid': gid}, 'client_id': 'tests'}
        self.assertFalse(cred.handle(request))

    def test_cred(self):
        parser = self.parser
        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_default')
        self.assertEqual(cred.uid, -1)
        self.assertEqual(cred.gid, -1)
        self.assertCredMismatch(cred, 0, 0)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_int')
        self.assertEqual(cred.uid, 0)
        self.assertEqual(cred.gid, 0)
        self.assertCredMatch(cred, 0, 0)
        self.assertCredMatch(cred, 0, self.group.gr_gid)
        self.assertCredMatch(cred, self.user.pw_uid, 0)
        self.assertCredMismatch(cred, self.user.pw_uid, self.group.gr_gid)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_root')
        self.assertEqual(cred.uid, 0)
        self.assertEqual(cred.gid, 0)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_user')
        self.assertEqual(cred.uid, 0)
        self.assertEqual(cred.gid, -1)
        self.assertCredMatch(cred, 0, 0)
        self.assertCredMismatch(cred, self.user.pw_uid, 0)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_group')
        self.assertEqual(cred.uid, -1)
        self.assertEqual(cred.gid, 0)
        self.assertCredMatch(cred, 0, 0)
        self.assertCredMismatch(cred, 0, self.group.gr_gid)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_other_int')
        self.assertNotEqual(cred.uid, 0)
        self.assertEqual(cred.uid, self.user.pw_uid)
        self.assertNotEqual(cred.gid, 0)
        self.assertEqual(cred.gid, self.group.gr_gid)

        cred = authenticators.SimpleCredsAuth(parser, 'auth:cred_other_name')
        self.assertNotEqual(cred.uid, 0)
        self.assertEqual(cred.uid, self.user.pw_uid)
        self.assertNotEqual(cred.gid, 0)
        self.assertEqual(cred.gid, self.group.gr_gid)

    def test_header(self):
        parser = self.parser
        hdr = authenticators.SimpleHeaderAuth(parser, 'auth:header_default')
        self.assertEqual(hdr.header, 'REMOTE_USER')
        self.assertEqual(hdr.value, None)

        hdr = authenticators.SimpleHeaderAuth(parser, 'auth:header_other')
        self.assertEqual(hdr.header, 'GSSAPI')
        self.assertEqual(hdr.value, None)

        hdr = authenticators.SimpleHeaderAuth(parser, 'auth:header_value')
        self.assertEqual(hdr.header, 'GSSAPI')
        self.assertEqual(hdr.value, {'admin'})

        hdr = authenticators.SimpleHeaderAuth(parser, 'auth:header_values')
        self.assertEqual(hdr.header, 'GSSAPI')
        self.assertEqual(hdr.value, {'admin', 'user'})
