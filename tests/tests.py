from __future__ import absolute_import

import unittest

from tests.custodia import CustodiaTests

from custodia.message.kem import KEMTests
from custodia.secrets import SecretsTests
from custodia.store.sqlite import SqliteStoreTests


if __name__ == '__main__':
    testLoad = unittest.TestLoader()

    allUnitTests = [testLoad.loadTestsFromTestCase(SecretsTests),
                    testLoad.loadTestsFromTestCase(SqliteStoreTests),
                    testLoad.loadTestsFromTestCase(KEMTests),
                    testLoad.loadTestsFromTestCase(CustodiaTests)]

    allTestsSuite = unittest.TestSuite(allUnitTests)

    testRunner = unittest.TextTestRunner()
    testRunner.run(allTestsSuite)
