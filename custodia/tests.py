from custodia.secrets import SecretsTests
import unittest

if __name__ == '__main__':
    testLoad = unittest.TestLoader()

    allUnitTests = [testLoad.loadTestsFromTestCase(SecretsTests)]

    allTestsSuite = unittest.TestSuite(allUnitTests)

    testRunner = unittest.TextTestRunner()
    testRunner.run(allTestsSuite)
