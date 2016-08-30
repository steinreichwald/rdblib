# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from pythonic_testcase import *

from ddc.tool.cdb_tool import ImageBatch
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

