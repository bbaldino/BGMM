# -*- coding: utf-8 -*-

"""
Single interface for code that varies across Python versions
"""

import sys

_ver = sys.version_info
is_py26 = (_ver[:2] == (2, 6))

if is_py26:
    from gmusicapi.utils.counter import Counter
    try:
        import unittest2 as unittest
    except:
        print "Error importing unittest2, ignoring"
    import json
else:  # 2.7
    from collections import Counter
    import unittest
    import json
