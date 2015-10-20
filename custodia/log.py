# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import logging
import sys

custodia_logger = logging.getLogger('custodia')
custodia_logger.addHandler(logging.NullHandler())


LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGING_AUDITFORMAT = "%(asctime)s %(message)s"
LOGGING_DATEFORMAT = "%Y-%m-%h %H:%M:%S"


def setup_logging(debug=False, auditlog='custodia.audit.log'):
    # prevent multiple stream handlers
    root_logger = logging.getLogger()
    if not any(isinstance(hdlr, logging.StreamHandler)
               for hdlr in root_logger.handlers):
        default_fmt = logging.Formatter(LOGGING_FORMAT, LOGGING_DATEFORMAT)
        stream_hdlr = logging.StreamHandler(sys.stderr)
        stream_hdlr.setFormatter(default_fmt)
        root_logger.addHandler(stream_hdlr)

    custodia_logger = logging.getLogger('custodia')
    if debug:
        custodia_logger.setLevel(logging.DEBUG)
        custodia_logger.debug('Custodia debug logger enabled')
    else:
        custodia_logger.setLevel(logging.INFO)

    audit_logger = logging.getLogger('custodia.audit')
    if len(audit_logger.handlers) == 0:
        audit_fmt = logging.Formatter(LOGGING_AUDITFORMAT, LOGGING_DATEFORMAT)
        audit_hdrl = logging.FileHandler(auditlog)
        audit_hdrl.setFormatter(audit_fmt)
        audit_logger.addHandler(audit_hdrl)

        custodia_logger.debug('Custodia audit log: %s', auditlog)


AUDIT_NONE = 0
AUDIT_GET_ALLOWED = 1
AUDIT_GET_DENIED = 2
AUDIT_SET_ALLOWED = 3
AUDIT_SET_DENIED = 4
AUDIT_DEL_ALLOWED = 5
AUDIT_DEL_DENIED = 6
AUDIT_LAST = 7
AUDIT_SVC_NONE = 8
AUDIT_SVC_AUTH_PASS = 9
AUDIT_SVC_AUTH_FAIL = 10
AUDIT_SVC_AUTHZ_PASS = 11
AUDIT_SVC_AUTHZ_FAIL = 12
AUDIT_SVC_LAST = 13
AUDIT_MESSAGES = [
    "AUDIT FAILURE",
    "ALLOWED: '%(client)s' requested key '%(key)s'",  # AUDIT_GET_ALLOWED
    "DENIED: '%(client)s' requested key '%(key)s'",   # AUDIT_GET_DENIED
    "ALLOWED: '%(client)s' stored key '%(key)s'",     # AUDIT_SET_ALLOWED
    "DENIED: '%(client)s' stored key '%(key)s'",      # AUDIT_SET_DENIED
    "ALLOWED: '%(client)s' deleted key '%(key)s'",    # AUDIT_DEL_ALLOWED
    "DENIED: '%(client)s' deleted key '%(key)s'",     # AUDIT_DEL_DENIED
    "AUDIT FAILURE 7",
    "AUDIT FAILURE 8",
    "PASS(%(tag)s): '%(cli)s' authenticated as '%(name)s'",  # SVC_AUTH_PASS
    "FAIL(%(tag)s): '%(cli)s' authenticated as '%(name)s'",  # SVC_AUTH_FAIL
    "PASS(%(tag)s): '%(cli)s' authorized for '%(name)s'",    # SVC_AUTHZ_PASS
    "FAIL(%(tag)s): '%(cli)s' authorized for '%(name)s'",    # SVC_AUTHZ_FAIL
    "AUDIT FAILURE 13",
]


class AuditLog(object):
    def __init__(self, logger):
        self.logger = logger

    def key_access(self, action, client, keyname):
        if action <= AUDIT_NONE or action >= AUDIT_LAST:
            action = AUDIT_NONE
        msg = AUDIT_MESSAGES[action]
        args = {'client': client, 'key': keyname}
        self.logger.info(msg, args)

    def svc_access(self, action, client, tag, name):
        if action <= AUDIT_SVC_NONE or action >= AUDIT_SVC_LAST:
            action = AUDIT_NONE
        msg = AUDIT_MESSAGES[action]
        args = {'cli': client, 'tag': tag, 'name': name}
        self.logger.info(msg, args)

auditlog = AuditLog(logging.getLogger('custodia.audit'))
