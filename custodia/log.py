# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import io
import sys
import traceback
import time


DEBUG = False


def stacktrace():
    with io.BytesIO() as f:
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb, None, file=f)
        del tb
        return f.getvalue()


def error(msg, head=None):
    if head is not None:
        t = time.gmtime(time.time())
        head = '%04d/%02d/%02d %02d:%02d:%02d' % (
            t[0], t[1], t[2], t[3], t[4], t[5])
    sys.stderr.write('[%s] %s\n' % (head, msg))


def debug(msg):
    if DEBUG:
        error(msg, 'DEBUG')
        sys.stderr.write(stacktrace())
