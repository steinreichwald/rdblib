# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os
from pathlib import Path

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *
from schwarz.fakefs_helpers import TempFS

import srw.rdblib
from ..testutil import create_ibf_with_tiffs
from srw.rdblib.lib import PIC
from .. import ImageBatch, TiffHandler
from ...paths import guess_path
from srw.rdblib.tiff.testutil import create_dual_page_tiff_file


# XXX add some tests for images. They are completely missing, and cdb_tool
# has the potential to hang on bad image files.

root_path = os.path.dirname(os.path.dirname(srw.rdblib.__path__[0]))
DATABASE_PATH = os.path.join(root_path, 'private', 'srw', 'data')
CDB_PATH = os.path.join(DATABASE_PATH, '00099201.CDB')

@DataDrivenTestCase
class TiffHandlerTest(PythonicTestCase):
    def setUp(self):
        self.fs = TempFS.set_up(test=self)
        self.data_dir = Path(self.fs.create_directory('data'))

    @data('write', 'copy')
    def test_tiff_access(self, access):
        ibf_path = self._create_ibf(n_images=1)

        fname = str(ibf_path)
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

    # --- internal helpers ----------------------------------------------------
    def _create_ibf(self, n_images=1):
        assert (n_images == 1)
        pic = PIC(year=2022, month=6, customer_id_short=123, counter=42)
        pic_str = pic.to_str(short_ik=True)
        tiff_file = create_dual_page_tiff_file(pic_str)
        tiff_bytes = tiff_file.to_bytes()
        ibf_path = self.data_dir / '00099201.IBF'

        create_ibf_with_tiffs([tiff_bytes], ibf_path=ibf_path)
        return ibf_path

