# -*- coding: utf-8 -*-

from collections import OrderedDict
import struct

from pythonic_testcase import *

from ..tag_specification import FT
from ..tags import TAG_SIZE
from ..tiff_file import TiffImage
from ..tiff_testutil import (bytes_from_tiff_writer, calc_offset, ifd_data,
    pad_string, to_bytes)



class TiffImageWritingTest(PythonicTestCase):
    def test_can_write_image_dimensions_with_short_data(self):
        img_data = b'dummy'
        tiff_img = TiffImage(tags={256: 1260, 257: 830}, img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        tag_data = (
            # 258: ImageWidth
            ('H', 256), ('H', FT.SHORT), ('i', 1), ('i', 1260),
            # 257: ImageLength
            ('H', 257), ('H', FT.SHORT), ('i', 1), ('i', 830),
            # 279: StripByteCounts
            ('H', 279), ('H', FT.LONG), ('i', 1), ('i', len(img_data)),
        )
        nr_tags = 3
        expected_ifd = to_bytes((
            ('H', nr_tags),
            ('%ds' % (nr_tags * TAG_SIZE), to_bytes(tag_data)),
            ('i', 0),       # next_ifd
        ))
        expected_bytes = expected_ifd + img_data
        assert_equals(expected_bytes, tiff_img_bytes)

    def test_can_write_mixed_short_and_long_data(self):
        img_data = b'dummy'
        document_name = pad_string('foo bar', length=20)
        tiff_img = TiffImage(tags={258: 1, 269: document_name}, img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 3
        expected_long_data = document_name
        tag_data = (
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 269: DocumentName
            ('H', 269), ('H', FT.ASCII), ('i', len(document_name)), ('i', calc_offset(nr_tags)),
            # 279: StripByteCounts
            ('H', 279), ('H', FT.LONG), ('i', 1), ('i', len(img_data)),
        )
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + img_data
        img_offset = calc_offset(nr_tags, long_data=expected_long_data)
        expected_size = img_offset + len(img_data)
        if len(tiff_img_bytes) != expected_size:
            # this eases debugging (nosetests will suppress this output for passing tests)
            print('serialized TiffImage image is too short (only %d bytes, should be %d bytes)' % (len(tiff_img_bytes), expected_size))
        assert_equals(img_data, tiff_img_bytes[img_offset:])
        assert_equals(expected_bytes, tiff_img_bytes)

    def test_can_write_rational_tag(self):
        img_data = b'dummy'
        tiff_img = TiffImage(tags={258: 1, 282: 200}, img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 3
        expected_long_data = struct.pack('<ii', 200, 1)
        tag_data = (
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 282: XResolution
            ('H', 282), ('H', FT.RATIONAL), ('i', 1), ('i', calc_offset(nr_tags)),
            # 279: StripByteCounts
            ('H', 279), ('H', FT.LONG), ('i', 1), ('i', len(img_data)),
        )
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + img_data
        assert_equals(expected_bytes, tiff_img_bytes)

    def test_can_specify_tag_order(self):
        img_data = b'dummy'
        tiff_img = TiffImage(tags=OrderedDict([(257, 830), (256, 1260)]), img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        tag_data = (
            # 257: ImageLength
            ('H', 257), ('H', FT.SHORT), ('i', 1), ('i', 830),
            # 256: ImageWidth
            ('H', 256), ('H', FT.SHORT), ('i', 1), ('i', 1260),
            # 279: StripByteCounts
            ('H', 279), ('H', FT.LONG), ('i', 1), ('i', len(img_data)),
        )
        nr_tags = 3
        expected_ifd = to_bytes((
            ('H', nr_tags),
            ('%ds' % (nr_tags * TAG_SIZE), to_bytes(tag_data)),
            ('i', 0),       # next_ifd
        ))
        expected_bytes = expected_ifd + img_data
        assert_equals(expected_bytes, tiff_img_bytes)


