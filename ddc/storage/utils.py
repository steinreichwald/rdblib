# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import mmap

__all__ = ['filecontent', 'DELETE']

class DELETE(object):
    pass

def filecontent(mmap_or_filelike):
    if isinstance(mmap_or_filelike, mmap.mmap):
        return mmap_or_filelike
    fp = mmap_or_filelike
    old_pos = fp.tell()
    fp.seek(0)
    content = fp.read()
    fp.seek(old_pos)
    return content

