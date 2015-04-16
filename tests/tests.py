from custodia.secrets import SecretsTests
from custodia.store.sqlite import SqliteStoreTests
import unittest

if __name__ == '__main__':
    testLoad = unittest.TestLoader()

    allUnitTests = [testLoad.loadTestsFromTestCase(SecretsTests),
                    testLoad.loadTestsFromTestCase(SqliteStoreTests)]

    allTestsSuite = unittest.TestSuite(allUnitTests)

    testRunner = unittest.TextTestRunner()
    testRunner.run(allTestsSuite)
