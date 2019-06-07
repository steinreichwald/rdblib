# -*- coding: utf-8 -*-

from pythonic_testcase import *

from srw.rdblib.binary_format import BinaryFormat
from ..tag_specification import FT
from ..tiff_file import TiffFile, TiffImage
from ..tiff_testutil import (adapt_values, bytes_from_tiff_writer, calc_offset,
    ifd_data, pad_string, _tag_StripByteCounts, _tag_StripOffsets)
from ..tiff_testutil import star_extract as _se



class TiffWritingTest(PythonicTestCase):
    def test_can_serialize_single_page_tiff(self):
        document_name = pad_string('doc1', length=20)
        img_data = b'img1'
        tiff_img = TiffImage(tags={258: 1, 269: document_name}, img_data=img_data)
        tiff_file = TiffFile(tiff_images=[tiff_img])
        tiff_bytes = bytes_from_tiff_writer(tiff_file)

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

        assert_equals(img_data, tiff_bytes[end_ifd:])

