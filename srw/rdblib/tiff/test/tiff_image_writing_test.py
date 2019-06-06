# -*- coding: utf-8 -*-

import struct

from pythonic_testcase import *

from ..tag_specification import FT
from ..tags import TAG_SIZE
from ..tiff_file import TiffImage
from ..tiff_testutil import (bytes_from_tiff_writer, calc_offset, ifd_data,
    pad_string, to_bytes)



class TiffImageWritingTest(PythonicTestCase):
    def test_can_write_image_dimensions_with_short_data(self):
        tag_data = (
            # 258: ImageWidth
            ('H', 256), ('H', FT.SHORT), ('i', 1), ('i', 1260),
            # 257: ImageLength
            ('H', 257), ('H', FT.SHORT), ('i', 1), ('i', 830),
        )
        nr_tags = 2
        expected_tag_data = to_bytes(tag_data)
        expected_ifd = to_bytes((
            ('H', nr_tags),
            ('%ds' % (nr_tags * TAG_SIZE), expected_tag_data), # tag_data
            ('i', 0),       # next_ifd
        ))
        img_data = b'dummy'
        expected_bytes = expected_ifd + img_data
        tiff_img = TiffImage(tags={256: 1260, 257: 830}, img_data=img_data)
        assert_equals(expected_bytes, bytes_from_tiff_writer(tiff_img))

    def test_can_write_mixed_short_and_long_data(self):
        document_name = pad_string('foo bar', length=20)
        nr_tags = 2
        tag_data = (
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 269: DocumentName
            ('H', 269), ('H', FT.ASCII), ('i', len(document_name)), ('i', calc_offset(nr_tags)),
        )
        expected_long_data = document_name
        img_data = b'dummy'
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + img_data

        tiff_img = TiffImage(tags={258: 1, 269: document_name}, img_data=img_data)
        img_bytes = bytes_from_tiff_writer(tiff_img)
        img_offset = calc_offset(nr_tags, long_data=expected_long_data)
        expected_size = img_offset + len(img_data)
        if len(img_bytes) != expected_size:
            # this eases debugging (nosetests will suppress this output for passing tests)
            print('serialized TiffImage image is too short (only %d bytes, should be %d bytes)' % (len(img_bytes), expected_size))
        assert_equals(img_data, img_bytes[img_offset:])
        assert_equals(expected_bytes, img_bytes)

    def test_can_write_rational_tag(self):
        nr_tags = 2
        tag_data = (
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 282: XResolution
            ('H', 282), ('H', FT.RATIONAL), ('i', 1), ('i', calc_offset(nr_tags)),
        )
        expected_long_data = struct.pack('<ii', 200, 1)
        img_data = b'dummy'
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + img_data

        tiff_img = TiffImage(tags={258: 1, 282: 200}, img_data=img_data)
        img_bytes = bytes_from_tiff_writer(tiff_img)
        assert_equals(expected_bytes, img_bytes)
