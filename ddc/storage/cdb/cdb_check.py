# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from ddc.lib.filesize import format_filesize
from ddc.lib.log_proxy import l_
from ddc.lib.result import Result
from .cdb_format import CDBFormat, CDB_ENCODING
from ddc.tool.cdb_tool import MMapFile

__all__ = ['open_cdb']

_100mb = 100 * 1024 * 1024

def open_cdb(cdb_path, *, field_names, access='write', log=None):
    log = l_(log)
    filesize = os.stat(cdb_path).st_size
    if filesize >= _100mb:
        size_str = format_filesize(filesize, locale='de')
        return _error('Die CDB-Datei ist defekt (%s groß)' % size_str)

    encode_ = lambda s: s.encode(CDB_ENCODING)
    b_field_names = tuple(map(encode_, field_names))
    bytes_batch_header = CDBFormat.batch_header_size()
    bytes_per_form = CDBFormat.form_header_size() + (len(b_field_names) * CDBFormat.field_size())
    expected_form_count = (filesize - bytes_batch_header) // bytes_per_form
    expected_file_size = bytes_batch_header + (expected_form_count * bytes_per_form)
    if expected_file_size != filesize:
        extra_bytes = filesize - expected_file_size
        msg = 'Die CDB hat eine ungewöhnliche Größe (%d Bytes zu viel bei %d Belegen)'
        return _error(msg % (extra_bytes, expected_form_count))

    try:
        cdb_fp = MMapFile(cdb_path, access=access, log=log)
    except OSError:
        return _error('Die CDB-Datei ist vermutlich noch in Bearbeitung.')
    return Result(True, cdb_fp=cdb_fp)

def _error(msg):
    return Result(False, cdb_fp=None, message=msg)
