# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from pythonic_testcase import *

from ddc.tool.cdb_tool import ImageBatch, TiffHandler
from ddc.storage.ibf.ibf_fixtures import create_ibf, IBFFile, IBFImage


class IBFFileTest(PythonicTestCase):
    def test_can_generate_ibf_file_with_single_scan(self):
        tiff_data = b'\x00' * 200
        ibf_image = IBFImage(tiff_data)
        ibf_batch = IBFFile([ibf_image])
        ibf_fp = BytesIO(ibf_batch.as_bytes())

        ibf_batch = ImageBatch(ibf_fp, access='read')
        assert_equals(1, ibf_batch.image_count())
        ibf_tiff_data = ibf_batch.get_tiff_image(0)
        assert_equals(tiff_data, ibf_tiff_data)

    def test_create_ibf_helper_function(self):
        ibf_fp = create_ibf(nr_images=3)
        ibf_batch = ImageBatch(ibf_fp, access='read')
        assert_equals(3, ibf_batch.image_count())

    def test_can_create_ibf_with_pic_numbers(self):
        pics = (
            '12345600100024',
            '12345600114024',
            '12345600130024'
        )
        ibf_fp = create_ibf(nr_images=3, pic_nrs=pics, fake_tiffs=False)

        ibf_batch = ImageBatch(ibf_fp, access='read')
        for i, pic in enumerate(pics):
            tiff = ibf_batch.image_entries[i]
            assert_equals(pic, tiff.rec.codnr,
                message='PIC in first header')
            # currently only the TiffHandler does the complicated offset
            # calculation to parse the tiff headers.
            tiff_handler = TiffHandler(ibf_batch, i)
            # ideally we would also test the "long_data" structures but these
            # are inside the actual tiff image which the fixtures module can't
            # generate currently.
            assert_not_equals(pic, tiff_handler.long_data.rec.page_name,
                message='if long_data contains the correct pic enable the next two asserts')
            #assert_equals(pic, tiff_handler.long_data.rec.page_name,
            #    message='PIC in first tiff header (unused?)')
            #assert_equals(pic, tiff_handler.long_data2.rec.page_name,
            #    message='PIC in second tiff header')
