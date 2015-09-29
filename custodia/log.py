# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import io
import sys
import time
import traceback


DEBUG = False


def stacktrace():
    with io.BytesIO() as f:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb, None, file=f)
        del tb
        return f.getvalue()


def get_time():
    t = time.gmtime(time.time())
    return '%04d/%02d/%02d %02d:%02d:%02d' % (
        t[0], t[1], t[2], t[3], t[4], t[5])


def error(msg, head=None):
    if head is not None:
        head = get_time()
    sys.stderr.write('[%s] %s\n' % (head, msg))


def debug(msg):
    if DEBUG:
        error(msg, 'DEBUG')
        sys.stderr.write(stacktrace())


AUDIT_NONE = 0
AUDIT_GET_ALLOWED = 1
AUDIT_GET_DENIED = 2
AUDIT_SET_ALLOWED = 3
AUDIT_SET_DENIED = 4
AUDIT_DEL_ALLOWED = 5
AUDIT_DEL_DENIED = 6
AUDIT_LAST = 7
AUDIT_MESSAGES = [
    "AUDIT FAILURE",
    "ALLOWED: '{client:s}' requested key '{key:s}'",  # AUDIT_GET_ALLOWED
    "DENIED: '{client:s}' requested key '{key:s}'",   # AUDIT_GET_DENIED
    "ALLOWED: '{client:s}' stored key '{key:s}'",     # AUDIT_SET_ALLOWED
    "DENIED: '{client:s}' stored key '{key:s}'",      # AUDIT_SET_DENIED
    "ALLOWED: '{client:s}' deleted key '{key:s}'",    # AUDIT_DEL_ALLOWED
    "DENIED: '{client:s}' deleted key '{key:s}'",     # AUDIT_DEL_DENIED
]


class AuditLog(object):

    def __init__(self, config):
        if config is None:
            config = {}
        self.logfile = config.get('auditlog', 'custodia.audit.log')

    def _log(self, message):
        with open(self.logfile, 'a+') as f:
            f.write('%s: %s\n' % (get_time(), message))
            f.flush()

    def key_access(self, action, client, keyname):
        if action <= AUDIT_NONE or action >= AUDIT_LAST:
            action = AUDIT_NONE
        self._log(AUDIT_MESSAGES[action].format(client=client, key=keyname))
