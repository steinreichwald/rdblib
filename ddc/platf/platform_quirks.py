# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import sys

# a little helper for mapping font sizes
def is_windows():
    return sys.platform == 'win32'

def is_linux():
    return sys.platform.startswith('linux')

def map_fontsize(size):
    if is_windows() or is_linux():
        size = size * 3 / 4
    return size

