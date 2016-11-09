# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from ddc.lib.filesize import format_filesize
from ddc.lib.log_proxy import l_
from ddc.lib.result import Result
from ddc.tool.cdb_tool import MMapFile


__all__ = ['open_cdb']

_100mb = 100 * 1024 * 1024

def open_cdb(cdb_path, *, access='write', log=None):
    log = l_(log)
    filesize = os.stat(cdb_path).st_size
    if filesize >= _100mb:
        size_str = format_filesize(filesize, locale='de')
        return _error('Die CDB-Datei ist defekt (%s groß)' % size_str)
    try:
        cdb_fp = MMapFile(cdb_path, access=access, log=log)
    except OSError:
        return _error('Die CDB-Datei ist vermutlich noch in Bearbeitung.')
    return Result(True, cdb_fp=cdb_fp)

def _error(msg):
    return Result(False, cdb_fp=None, message=msg)
