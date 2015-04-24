from __future__ import absolute_import
from custodia.secrets import SecretsTests
from custodia.store.sqlite import SqliteStoreTests
from custodia.message.kem import KEMTests
from tests.custodia import CustodiaTests
import unittest

if __name__ == '__main__':
    testLoad = unittest.TestLoader()

    allUnitTests = [testLoad.loadTestsFromTestCase(SecretsTests),
                    testLoad.loadTestsFromTestCase(SqliteStoreTests),
                    testLoad.loadTestsFromTestCase(KEMTests),
                    testLoad.loadTestsFromTestCase(CustodiaTests)]

    allTestsSuite = unittest.TestSuite(allUnitTests)

    testRunner = unittest.TextTestRunner()
    testRunner.run(allTestsSuite)
