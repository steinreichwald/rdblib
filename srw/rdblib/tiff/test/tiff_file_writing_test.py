# -*- coding: utf-8 -*-

from io import BytesIO

from PIL import Image
from pythonic_testcase import *

from srw.rdblib.binary_format import BinaryFormat
from ..tag_specification import FT
from ..tiff_file import align_to_8_offset, TiffFile, TiffImage
from ..tiff_testutil import (adapt_values, calc_offset, ifd_data, load_tiff_img,
    _tag_StripByteCounts, _tag_StripOffsets)
from ..tiff_testutil import star_extract as _se
from ..tiff_util import pad_tiff_bytes



class TiffWritingTest(PythonicTestCase):
    def test_can_serialize_single_page_tiff(self):
        document_name = pad_tiff_bytes('doc1', length=20)
        img_data = b'img1'
        tiff_img = TiffImage(tags={258: 1, 269: document_name}, img_data=img_data)
        tiff_file = TiffFile(tiff_images=[tiff_img])
        tiff_bytes = tiff_file.to_bytes()

        header_values = adapt_values({'byte_order': b'II', 'version': 42, 'first_ifd': 8}, TiffFile.header)
        expected_header = BinaryFormat(TiffFile.header).to_bytes(header_values)
        assert_equals(expected_header, tiff_bytes[:8])

        expected_long_data = document_name
        nr_tags = 4
        tag_data = _se(
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 269: DocumentName
            ('H', 269), ('H', FT.ASCII), ('i', len(document_name)), ('i', calc_offset(nr_tags, offset=8)),
            _tag_StripOffsets(nr_tags, expected_long_data, offset=8),
            _tag_StripByteCounts(img_data),
        )
        expected_ifd_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data)
        end_ifd = len(expected_header) + len(expected_ifd_bytes)
        actual_ifd_bytes = tiff_bytes[8:end_ifd]
        assert_equals(expected_ifd_bytes, actual_ifd_bytes)

        nr_pad_bytes = align_to_8_offset(end_ifd)
        assert_equals(img_data, tiff_bytes[end_ifd+nr_pad_bytes:])

    def test_serialized_tiff_file_can_be_loaded_with_pillow(self):
        # pillow needs actual image data
        img = load_tiff_img()
        img.tags[269] = b'name\x00'
        (width, height) = img.size

        tiff_img = TiffImage(tags=img.tags, img_data=img.data)
        tiff_file = TiffFile(tiff_images=[tiff_img])
        tiff_bytes = tiff_file.to_bytes()

        pillow_img = Image.open(BytesIO(tiff_bytes))
        assert_equals((width, height), pillow_img.size)
        assert_equals(1, pillow_img.n_frames)

        img_tags = dict(pillow_img.tag_v2.items())
        assert_equals(width, img_tags.get(256))
        assert_equals(height, img_tags.get(257))
        assert_equals('name', img_tags.get(269))

    def test_can_serialize_multi_page_tiff(self):
        img = load_tiff_img()
        tiff_img1 = TiffImage(tags=img.tags, img_data=img.data)
        img2 = load_tiff_img()
        tiff_img2 = TiffImage(tags=img2.tags, img_data=img2.data)
        tiff_file = TiffFile(tiff_images=[tiff_img1, tiff_img2])
        tiff_bytes = tiff_file.to_bytes()

        pillow_img = Image.open(BytesIO(tiff_bytes))
        assert_equals(img.size, pillow_img.size)
        assert_equals(2, pillow_img.n_frames)

