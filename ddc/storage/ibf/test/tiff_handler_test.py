# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *

import ddc
from ddc.storage.ibf import ImageBatch, TiffHandler
from ddc.storage.paths import guess_path


# XXX add some tests for images. They are completely missing, and cdb_tool
# has the potential to hang on bad image files.

DATABASE_PATH = os.path.join(ddc.rootpath, 'private', 'srw', 'data')
CDB_PATH = os.path.join(DATABASE_PATH, '00099201.CDB')

@DataDrivenTestCase
class TiffHandlerTest(PythonicTestCase):
    @data('write', 'copy')
    def test_tiff_access(self, access):
        if not os.path.exists(CDB_PATH):
            raise SkipTest('private data not available')
        fname = guess_path(CDB_PATH, 'IBF')
        imbatch = ImageBatch(fname, access=access)
        th = TiffHandler(imbatch, 0)
        assert_equals(27, th.ifd.rec.num_tags)
        assert_equals('REZEPT', th.long_data.rec.document_name)
        assert_equals(27, th.ifd2.rec.num_tags)
        assert_equals('REZEPT', th.long_data2.rec.document_name)

    @data('write', 'copy')
    def test_tiff_write(self, access):
        if not os.path.exists(CDB_PATH):
            raise SkipTest('private data not available')
        fname = guess_path(CDB_PATH, 'IBF')
        imbatch = ImageBatch(fname, access=access)
        th = TiffHandler(imbatch, 0)
        th.long_data.update_rec(page_name = 'DELETED')
        th.update()
        th = TiffHandler(imbatch, 1)
        assert_not_equals('DELETED', th.long_data.rec.page_name)

        th = TiffHandler(imbatch, 0)
        assert_equals('DELETED', th.long_data.rec.page_name)
        undone = th.long_data2.rec.page_name
        th.long_data.update_rec(page_name = undone)
        th.update()
