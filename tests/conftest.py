# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import logging
import warnings

import pytest

from custodia.log import ProvisionalWarning, setup_logging

# deprecated APIs raise an exception
warnings.simplefilter('error', category=DeprecationWarning)
# ignore pytest warnings
warnings.filterwarnings('ignore', category=DeprecationWarning,
                        module=r'_pytest\..*')
# silence our own warnings about provisional APIs
warnings.simplefilter('ignore', category=ProvisionalWarning)


# don't spam stderr with log messages
logging.getLogger().handlers[:] = []
setup_logging(debug=False, auditfile=None, handler=logging.NullHandler())

SKIP_SERVERTEST = "--skip-servertests"


def pytest_addoption(parser):
    parser.addoption(
        SKIP_SERVERTEST,
        action="store_true",
        help="Skip integration tests"
    )


def pytest_runtest_setup(item):
    skip_servertest = item.config.getoption(SKIP_SERVERTEST)
    skiptest = False
    if skip_servertest:
        # pytest < 4
        if hasattr(item, 'get_marker'):
            if item.get_marker("servertest"):
                skiptest = True
        # pytest >= 4
        elif item.get_closest_marker("servertest"):
            skiptest = True

    if skiptest:
        # args has --skip-servertests and test is marked as servertest
        pytest.skip("Skip integration test")
