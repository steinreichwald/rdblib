# -*- coding: utf-8 -*-

from pathlib import Path

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *
from schwarz.fakefs_helpers import TempFS

from ..testutil import create_ibf_with_tiffs
from srw.rdblib.lib import PIC
from .. import ImageBatch, TiffHandler
from srw.rdblib.tiff.testutil import create_dual_page_tiff_file



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
        ibf_path = self._create_ibf(n_images=2)

        fname = str(ibf_path)
        ibf = ImageBatch(fname, access=access)
        th = TiffHandler(ibf, 0)
        th.long_data.update_rec(page_name = 'DELETED')
        th.update()
        th = TiffHandler(ibf, 1)
        assert_not_equals('DELETED', th.long_data.rec.page_name)

        th = TiffHandler(ibf, 0)
        assert_equals('DELETED', th.long_data.rec.page_name)
        undone = th.long_data2.rec.page_name
        th.long_data.update_rec(page_name = undone)
        th.update()

    # --- internal helpers ----------------------------------------------------
    def _create_ibf(self, n_images=1):
        pic = PIC(year=2022, month=6, customer_id_short=123, counter=42)
        tiffs = []
        for i in range(n_images):
            pic = pic + 1
            pic_str = pic.to_str(short_ik=True)
            tiff_file = create_dual_page_tiff_file(pic_str)
            tiff_bytes = tiff_file.to_bytes()
            tiffs.append((pic_str, tiff_bytes))

        ibf_path = self.data_dir / '00099201.IBF'
        create_ibf_with_tiffs(tiffs, ibf_path=ibf_path)
        return ibf_path

