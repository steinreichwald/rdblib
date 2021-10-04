# -*- coding: utf-8 -*-

from unittest import TestCase

from PIL import Image
from pythonic_testcase import *

from srw.rdblib.lib import PIC
from ..tiff_api import pic_from_tiff
from ..testutil import load_tiff_dummy_bytes, path_dummy_tiff



class PICFromTIFFTest(TestCase):
    def test_can_read_pic_from_tiff_file_on_disk(self):
        expected_pic_str = '20503500001024'
        path = path_dummy_tiff()
        for tiff_path in (path, str(path)):
            pic = pic_from_tiff(tiff_path)
            assert_isinstance(pic, PIC)
            assert_equals(expected_pic_str, str(pic))

    def test_can_read_pic_tiff_bytes(self):
        expected_pic_str = '20503500001024'
        tiff_bytes = load_tiff_dummy_bytes()
        pic = pic_from_tiff(tiff_bytes)
        assert_equals(expected_pic_str, str(pic))

    def test_can_read_pic_from_pillow_img(self):
        expected_pic_str = '20503500001024'
        tiff_path = path_dummy_tiff()
        img = Image.open(tiff_path)
        pic = pic_from_tiff(img)
        assert_equals(expected_pic_str, str(pic))

