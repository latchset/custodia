# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
import warnings

from custodia.plugin import DEFAULT_CTYPE, HTTPConsumer, SUPPORTED_COMMANDS


__all__ = ('DEFAULT_CTYPE', 'SUPPORTED_COMMANDS', 'HTTPConsumer')


warnings.warn('custodia.httpd.consumer is deprecated, import from '
              'custodia.plugin instead.', DeprecationWarning)
