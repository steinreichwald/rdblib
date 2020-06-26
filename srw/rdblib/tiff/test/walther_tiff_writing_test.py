# -*- coding: utf-8 -*-

from io import BytesIO

from pythonic_testcase import *

from srw.rdblib.ibf import IBFFile, IBFImage, ImageBatch, TiffHandler
from ..tiff_file import TiffFile
from ..tiff_testutil import load_tiff_img
from ..walther_tiff import WaltherTiff


class WaltherTiffWritingTest(PythonicTestCase):
    def test_can_read_pic_from_generated_multipage_tiff(self):
        pic_str = '90212304321024'
        ibf = self._create_ibf_with_tiff(pic_str)

        assert_equals(1, ibf.image_count())
        form_idx = 0
        th = TiffHandler(ibf, form_idx)
        assert_equals(pic_str, th.long_data.rec.page_name)
        assert_equals(pic_str, th.long_data2.rec.page_name)

    def _create_ibf_with_tiff(self, pic_str):
        img1 = load_tiff_img()
        width, height = img1.size
        tiff_img1 = WaltherTiff.create(width=width, height=height, img_data=img1.data, pic=pic_str)

        img2 = load_tiff_img()
        tiff_img2 = WaltherTiff.create(width=width, height=height, img_data=img2.data, pic=pic_str)
        tiff_file = TiffFile(tiff_images=[tiff_img1, tiff_img2])
        tiff_bytes = tiff_file.to_bytes()
        ibf_image = IBFImage(tiff_bytes)
        ibf_batch = IBFFile([ibf_image])
        ibf_fp = BytesIO(ibf_batch.as_bytes())
        ibf = ImageBatch(ibf_fp)
        return ibf
