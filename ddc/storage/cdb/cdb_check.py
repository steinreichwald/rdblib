# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from ddc.lib.log_proxy import l_
from ddc.lib.result import Result
from ddc.tool.cdb_tool import MMapFile


def open_cdb(cdb_path, *, access='write', log=None):
    log = l_(log)
    try:
        cdb_fp = MMapFile(cdb_path, access=access, log=log)
    except OSError:
        return Result(False, cdb_fp=None,
            message='Die CDB-Datei ist vermutlich noch in Bearbeitung.')
    return Result(True, cdb_fp=cdb_fp)
