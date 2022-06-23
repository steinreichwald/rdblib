# -*- coding: utf-8 -*-

from io import BytesIO

from PIL import Image, ImageDraw
from pythonic_testcase import *

from srw.rdblib.ibf import IBFFile, IBFImage, ImageBatch, TiffHandler
from srw.rdblib.lib import PIC
from ..tag_specification import TIFF_TAG as TT
from ..tiff_api import pic_from_tiff
from ..tiff_file import TiffFile
from ..tiff_creation import pil_image_as_walther_tiff



class WaltherTiffCreationTest(PythonicTestCase):
    def test_can_create_walther_tiff_from_pillow_image(self):
        w_h = (1250, 830)
        img = Image.new('RGB', w_h, color='white')
        d = ImageDraw.Draw(img)
        d.text((600, 750), 'foobar', fill='black')

        pic = PIC(year=2022, month=6, customer_id_short=123, counter=42)
        walther_tiff = pil_image_as_walther_tiff(img, pic)
        tiff_file = TiffFile(tiff_images=[walther_tiff, walther_tiff])
        tiff_bytes = tiff_file.to_bytes()
        tiff_fp = BytesIO(tiff_bytes)

        assert_equals(pic, pic_from_tiff(tiff_fp))
        tiff_fp.seek(0)

        pillow_img = Image.open(tiff_fp)
        pic_str = pic.to_str(short_ik=True)
        tiff_tags = dict(pillow_img.tag_v2.items())
        assert_equals(pic_str, tiff_tags[TT.PageName].rstrip('\x00'))
        assert_equals(
            'Rechenzentrum für Berliner Apotheken Stein & Reichwald GmbH',
            tiff_tags[TT.Artist].rstrip('\x00')
        )

        ibf = create_image_batch_with_tiffs([tiff_bytes])
        form_idx = 0
        th = TiffHandler(ibf, form_idx)
        assert_equals(pic_str, th.long_data.rec.page_name)
        assert_equals(pic_str, th.long_data2.rec.page_name)



def create_image_batch_with_tiffs(tiff_bytes):
    ibf_images = [IBFImage(_tiff) for _tiff in tiff_bytes]
    ibf_file = IBFFile(ibf_images)
    ibf_fp = BytesIO(ibf_file.as_bytes())
    ibf = ImageBatch(ibf_fp)
    return ibf

