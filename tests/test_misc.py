# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import logging.handlers

import pkg_resources

import pytest

from custodia import log

# pylint: disable=redefined-outer-name

PYTEST_VERSION = tuple(int(p) for p in pytest.__version__.split('.'))

if PYTEST_VERSION < (2, 10):
    yield_fixture = pytest.yield_fixture
else:
    yield_fixture = pytest.fixture


@yield_fixture
def loghandler(request):
    orig_handlers = logging.getLogger().handlers[:]
    handler = logging.handlers.BufferingHandler(10240)
    log.setup_logging(debug=False, auditfile=None, handler=handler)
    yield handler
    logging.getLogger().handlers = orig_handlers


def test_import_about():
    from custodia import __about__

    assert __about__.__title__ == 'custodia'
    dist = pkg_resources.get_distribution('custodia')
    assert dist.version == __about__.__version__  # pylint: disable=no-member


def test_logging_info(loghandler):
    testlogger = log.getLogger('custodia.test')
    assert testlogger.getEffectiveLevel() == logging.INFO
    try:
        raise ValueError('testmsg')
    except ValueError:
        testlogger.exception('some message')
    assert len(loghandler.buffer) == 1
    msg = loghandler.format(loghandler.buffer[0])
    loghandler.flush()
    assert msg.endswith('some message (ValueError: testmsg)')
    assert "Traceback" not in msg


def test_logging_debug(loghandler):
    testlogger = log.getLogger('custodia.test')
    testlogger.setLevel(logging.DEBUG)
    try:
        raise ValueError('testmsg with stack')
    except ValueError:
        testlogger.exception('some message')
    assert len(loghandler.buffer) == 1
    msg = loghandler.format(loghandler.buffer[0])
    loghandler.flush()
    assert "some message" in msg
    assert "Traceback (most recent call last):\n" in msg
    assert "ValueError: testmsg with stack" in msg
