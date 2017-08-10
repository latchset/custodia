# Copyright (C) 2017  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import socket
import ssl

import pytest

from custodia.httpd import server

CONFIG = {
    'consumers': {
        'dummy': None
    },
    'tls_certfile': 'tests/ca/custodia-server.pem',
    'tls_keyfile': 'tests/ca/custodia-server.key',
    'tls_cafile': 'tests/ca/custodia-ca.pem',
}
LOCALADDR = ('127.0.0.1', 0)


def test_tlserver():
    # pylint: disable=protected-access
    config = CONFIG.copy()
    srv = server.ForkingTLSServer(
        LOCALADDR,
        server.HTTPRequestHandler,
        config,
        bind_and_activate=False
    )
    assert srv.socket
    assert srv.socket.family == socket.AF_INET
    assert srv._context.verify_mode == ssl.CERT_NONE

    config['tls_verify_client'] = True
    srv = server.ForkingTLSServer(
        LOCALADDR,
        server.HTTPRequestHandler,
        config,
        bind_and_activate=False
    )
    assert srv._context.verify_mode == ssl.CERT_REQUIRED

    config['tls_certfile'] = 'nonexisting/file'
    pytest.raises(
        IOError,
        server.ForkingTLSServer,
        LOCALADDR,
        server.HTTPRequestHandler,
        config,
        bind_and_activate=False
    )
