from custodia.secrets import SecretsTests
from custodia.store.sqlite import SqliteStoreTests
from custodia.message.kem import KEMTests
import unittest

if __name__ == '__main__':
    testLoad = unittest.TestLoader()

    allUnitTests = [testLoad.loadTestsFromTestCase(SecretsTests),
                    testLoad.loadTestsFromTestCase(SqliteStoreTests),
                    testLoad.loadTestsFromTestCase(KEMTests)]

    allTestsSuite = unittest.TestSuite(allUnitTests)

    testRunner = unittest.TextTestRunner()
    testRunner.run(allTestsSuite)
