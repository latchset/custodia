# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os
import subprocess
import sys
import unittest

import six


class TestsCommandLine(unittest.TestCase):
    def _custodia_cli(self, *args):
        env = os.environ.copy()
        env['PYTHONPATH'] = './'
        pexec = env.get('CUSTODIAPYTHON', sys.executable)
        cli = [
            pexec,
            '-Wignore',
            '-m', 'custodia.cli',
            '--debug'
        ]
        cli.extend(args)

        try:
            # Python 2.7 doesn't have CalledProcessError.stderr
            output = subprocess.check_output(
                cli, env=env, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            output = e.output
            if not isinstance(e.output, six.text_type):
                e.output = e.output.decode('utf-8')
            raise
        else:
            if not isinstance(output, six.text_type):
                output = output.decode('utf-8')
            return output

    def test_help(self):
        output = self._custodia_cli('--help')
        self.assertIn(u'Custodia command line interface', output)

    def test_connection_error_with_server_option(self):
        invalid_server_name = 'http://custodia.invalid/secrets/key'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self._custodia_cli('--server',
                               invalid_server_name,
                               'ls',
                               '/')
        self.assertIn(invalid_server_name, cm.exception.output)

    def test_connection_error_with_uds_urlpath_option(self):
        invalid_path_name = 'path/to/file'
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self._custodia_cli('--uds-urlpath',
                               invalid_path_name,
                               'ls',
                               '/')
        self.assertIn(invalid_path_name, cm.exception.output)

    def test_plugins(self):
        output = self._custodia_cli('plugins')
        self.assertIn(u'[custodia.authenticators]', output)
        self.assertIn(u'[custodia.authorizers]', output)
        self.assertIn(u'[custodia.clients]', output)
        self.assertIn(u'[custodia.consumers]', output)
        self.assertIn(u'[custodia.stores]', output)
