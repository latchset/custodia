# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file
from __future__ import absolute_import

import pkg_resources


def test_import_about():
    from custodia import __about__

    assert __about__.__title__ == 'custodia'
    dist = pkg_resources.get_distribution('custodia')
    assert dist.version == __about__.__version__  # pylint: disable=no-member
