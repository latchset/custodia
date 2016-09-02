# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file

import abc
import configparser
import grp
import logging
import pwd

from jwcrypto.common import json_encode

import six

from .log import auditlog


logger = logging.getLogger(__name__)


REQUIRED = object()


class CustodiaException(Exception):
    pass


class HTTPError(CustodiaException):
    def __init__(self, code=None, message=None):
        self.code = code if code is not None else 500
        self.mesg = message
        errstring = '%d: %s' % (self.code, self.mesg)
        logger.debug(errstring)
        super(HTTPError, self).__init__(errstring)


class CSStoreError(CustodiaException):
    def __init__(self, message=None):
        logger.debug(message)
        super(CSStoreError, self).__init__(message)


class CSStoreExists(CustodiaException):
    def __init__(self, message=None):
        logger.debug(message)
        super(CSStoreExists, self).__init__(message)


class OptionHandler(object):
    def __init__(self, config, section):
        self.config = config
        self.section = section

    def get(self, name, typ, default, doc):
        if typ in {str, int, float, bool}:
            typ = typ.__name__
        if (default is REQUIRED and
                not self.config.has_option(self.section, name)):
            raise NameError(self.section, name)
        handler = getattr(self, '_get_{}'.format(typ), None)
        if handler is None:
            raise ValueError(typ)
        return handler(name, default)

    def _get_int(self, name, default):
        return self.config.getint(self.section, name, fallback=default)

    def _get_float(self, name, default):
        return self.config.getfloat(self.section, name, fallback=default)

    def _get_bool(self, name, default):
        return self.config.getboolean(self.section, name, fallback=default)

    def _get_str(self, name, default):
        return self.config.get(self.section, name, fallback=default)

    def _get_str_set(self, name, default):
        try:
            value = self.config.get(self.section, name)
        except configparser.NoOptionError:
            return default
        if not value or not value.strip():
            return None
        else:
            return set(v.strip() for v in value.split(','))

    def _get_store(self, name, default):
        return self.config.get(self.section, name, fallback=default)

    def _get_pwd_uid(self, name, default):
        value = self.config.get(self.section, name, fallback=default)
        try:
            return int(value)
        except ValueError:
            return pwd.getpwnam(value).pw_uid

    def _get_grp_gid(self, name, default):
        value = self.config.get(self.section, name, fallback=default)
        try:
            return int(value)
        except ValueError:
            return grp.getgrnam(value).gr_gid


@six.add_metaclass(abc.ABCMeta)
class CustodiaPlugin(object):
    options = None

    def __init__(self, config=None, section=None):
        origin, debug = self._configure(config, section)
        self._auditlog = auditlog
        self.origin = origin
        l = logging.getLogger(
            'custodia.plugins.%s' % self.__class__.__name__)
        l.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger = logging.LoggerAdapter(l, {'origin': self.origin})

    def audit_key_access(self, *args, **kwargs):
        self._auditlog.key_access(self.origin, *args, **kwargs)

    def audit_svc_access(self, *args, **kwargs):
        self._auditlog.svc_access(self.origin, *args, **kwargs)

    def _configure(self, config, section):
        if self.options is not None:
            # new style configuration
            opt = OptionHandler(config, section)
            # pylint: disable=not-an-iterable
            for name, typ, default, doc in self.options:
                # no name clashes
                if getattr(self, name, None):
                    raise NameError(name)
                value = opt.get(name, typ, default, doc)
                # special case for store
                if typ == 'store':
                    if name != 'store':
                        raise ValueError(name)
                    self.store_name = value
                    self.store = None
                else:
                    setattr(self, name, value)

            origin = '%s-[%s]' % (type(self).__name__, section)
            debug = opt.get('debug', bool, False, '')
        else:
            # old style configuration
            if config is None:
                config = {}
            self.config = config
            origin = config.get('facility_name', self.__class__.__name__)
            debug = config.get('debug', 'false').lower() == 'true'

        return origin, debug


class CSStore(CustodiaPlugin):
    @abc.abstractmethod
    def get(self, key):
        pass

    @abc.abstractmethod
    def set(self, key, value, replace=False):
        pass

    @abc.abstractmethod
    def span(self, key):
        pass

    @abc.abstractmethod
    def list(self, keyfilter=None):
        pass

    @abc.abstractmethod
    def cut(self, key):
        pass


class HTTPAuthorizer(CustodiaPlugin):
    def __init__(self, config=None, section=None):
        super(HTTPAuthorizer, self).__init__(config, section)
        self.store_name = None
        if self.config and 'store' in self.config:
            self.store_name = self.config['store']
        self.store = None

    @abc.abstractmethod
    def handle(self, request):
        pass


class HTTPAuthenticator(CustodiaPlugin):
    @abc.abstractmethod
    def handle(self, request):
        pass


DEFAULT_CTYPE = 'text/html; charset=utf-8'
SUPPORTED_COMMANDS = ['GET', 'PUT', 'POST', 'DELETE']


class HTTPConsumer(CustodiaPlugin):
    def __init__(self, config=None, section=None):
        super(HTTPConsumer, self).__init__(config, section)
        self.store_name = None
        if config and 'store' in config:
            self.store_name = config['store']
        self.store = None
        self.subs = dict()
        self.root = self

    def add_sub(self, name, sub):
        self.subs[name] = sub
        if hasattr(sub, 'root'):
            sub.root = self.root

    def _find_handler(self, request):
        base = self
        command = request.get('command', 'GET')
        if command not in SUPPORTED_COMMANDS:
            raise HTTPError(501)
        trail = request.get('trail', None)
        if trail is not None:
            for comp in trail:
                subs = getattr(base, 'subs', {})
                if comp in subs:
                    base = subs[comp]
                    trail.pop(0)
                else:
                    break

        handler = getattr(base, command)
        if handler is None:
            raise HTTPError(400)

        return handler

    def handle(self, request):
        handler = self._find_handler(request)
        response = {'headers': dict()}

        # Handle request
        output = handler(request, response)
        if output is None:
            output = response.get('output')

        ct = response['headers'].get('Content-Type')
        if ct is None:
            ct = response['headers']['Content-Type'] = DEFAULT_CTYPE

        if 'application/json' in ct and isinstance(output, (dict, list)):
            output = json_encode(output).encode('utf-8')
            response['headers']['Content-Length'] = str(len(output))

        response['output'] = output

        if output is not None and not hasattr(output, 'read') \
                and not isinstance(output, six.binary_type):
            msg = "Handler {} returned unsupported type {} ({}):\n{!r}"
            raise TypeError(msg.format(handler, type(output), ct, output))

        if output is not None and 'Content-Length' not in response['headers']:
            if hasattr(output, 'read'):
                # LOG: warning file-type objects should set Content-Length
                pass
            else:
                response['headers']['Content-Length'] = str(len(output))

        return response
