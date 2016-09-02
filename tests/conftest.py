# Copyright (C) 2016  Custodia Project Contributors - see LICENSE file
import warnings

from custodia.log import ProvisionalWarning

# silence our own warnings about provisional APIs
warnings.simplefilter('ignore', category=ProvisionalWarning)
# deprecated APIs raise an exception
warnings.simplefilter('error', category=DeprecationWarning)
