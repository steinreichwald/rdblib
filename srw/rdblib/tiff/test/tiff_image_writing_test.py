# -*- coding: utf-8 -*-

from collections import OrderedDict
import struct

from pythonic_testcase import *

from ..tag_specification import FT
from ..tags import TAG_SIZE
from ..tiff_file import TiffImage
from ..tiff_testutil import (bytes_from_tiff_writer, calc_offset, ifd_data,
    pad_string, padding, _tag_StripByteCounts, _tag_StripOffsets, to_bytes)
from ..tiff_testutil import star_extract as _se



class TiffImageWritingTest(PythonicTestCase):
    def test_can_write_image_dimensions_with_short_data(self):
        img_data = b'dummy'
        tiff_img = TiffImage(tags={256: 1260, 257: 830}, img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 4
        tag_data = _se(
            # 258: ImageWidth
            ('H', 256), ('H', FT.SHORT), ('i', 1), ('i', 1260),
            # 257: ImageLength
            ('H', 257), ('H', FT.SHORT), ('i', 1), ('i', 830),
            _tag_StripOffsets(nr_tags),
            _tag_StripByteCounts(img_data),
        )
        expected_ifd = to_bytes((
            ('H', nr_tags),
            ('%ds' % (nr_tags * TAG_SIZE), to_bytes(tag_data)),
            ('i', 0),       # next_ifd
        ))
        expected_bytes = expected_ifd + padding(2) + img_data
        assert_equals(expected_bytes, tiff_img_bytes)

    def test_can_write_mixed_short_and_long_data(self):
        img_data = b'dummy'
        document_name = pad_string('foo bar', length=20)
        tiff_img = TiffImage(tags={258: 1, 269: document_name}, img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 4
        expected_long_data = document_name
        tag_data = _se(
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 269: DocumentName
            ('H', 269), ('H', FT.ASCII), ('i', len(document_name)), ('i', calc_offset(nr_tags)),
            _tag_StripOffsets(nr_tags, expected_long_data),
            _tag_StripByteCounts(img_data),
        )
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + padding(6) + img_data
        img_offset = calc_offset(nr_tags, long_data=expected_long_data, padding=True)

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

        nr_tags = 4
        expected_long_data = struct.pack('<ii', 200, 1)
        tag_data = _se(
            # 258: BitsPerSample
            ('H', 258), ('H', FT.SHORT), ('i', 1), ('i', 1),
            # 282: XResolution
            ('H', 282), ('H', FT.RATIONAL), ('i', 1), ('i', calc_offset(nr_tags)),
            _tag_StripOffsets(nr_tags, expected_long_data),
            _tag_StripByteCounts(img_data),
        )
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + padding(2) + img_data
        assert_equals(expected_bytes, tiff_img_bytes)

    def test_can_specify_tag_order(self):
        img_data = b'dummy'
        tiff_img = TiffImage(tags=OrderedDict([(257, 830), (256, 1260)]), img_data=img_data)
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 4
        tag_data = _se(
            # 257: ImageLength
            ('H', 257), ('H', FT.SHORT), ('i', 1), ('i', 830),
            # 256: ImageWidth
            ('H', 256), ('H', FT.SHORT), ('i', 1), ('i', 1260),
            _tag_StripOffsets(nr_tags),
            _tag_StripByteCounts(img_data),
        )
        expected_ifd = to_bytes((
            ('H', nr_tags),
            ('%ds' % (nr_tags * TAG_SIZE), to_bytes(tag_data)),
            ('i', 0),       # next_ifd
        ))
        expected_bytes = expected_ifd + padding(2) + img_data
        assert_equals(expected_bytes, tiff_img_bytes)


    def test_can_specify_order_of_long_data(self):
        "Test that the order of the long data can be specified explicitely"
        document_name = pad_string('invoice', length=20)
        software = pad_string('generator', length=40)
        page_name = pad_string('cover', length=30)
        img_data = b'dummy'
        tiff_img = TiffImage(
            tags=OrderedDict([(269, document_name), (285, page_name), (305, software)]),
            # Explicitely omit "285" (PageName) from "long_order" to ensure
            # the code can handle missing tags (and just uses the tag order).
            # This is helpful to make the code more robust (if the caller
            # forgets to list some tags) and helps reducing boilerplate code
            # on the caller's side (if the special ordering affects only the
            # first fields fields, just list these and the rest fails in place
            # naturally).
            long_order=(305, 269),
            img_data=img_data,
        )
        tiff_img_bytes = bytes_from_tiff_writer(tiff_img)

        nr_tags = 5
        expected_long_data = software + document_name + page_name
        offset_software = calc_offset(nr_tags)
        offset_document_name = offset_software + len(software)
        tag_data = _se(
            # 269: DocumentName
            # long data has "software" before "document_name" so we need to calculate the right offset
            ('H', 269), ('H', FT.ASCII), ('i', len(document_name)), ('i', offset_document_name),
            # 285: PageName
            # this tag was not specified in "long_order" so it should be the last one
            ('H', 285), ('H', FT.ASCII), ('i', len(page_name)), ('i', offset_document_name + len(document_name)),
            # 305: Software
            ('H', 305), ('H', FT.ASCII), ('i', len(software)), ('i', offset_software),
            _tag_StripOffsets(nr_tags, expected_long_data),
            _tag_StripByteCounts(img_data),
        )
        expected_bytes = ifd_data(nr_tags, tag_data, long_data=expected_long_data) + padding(4) + img_data
        expected_ifd_bytes = expected_bytes[:offset_software]
        ifd_bytes = tiff_img_bytes[:offset_software]
        assert_equals(expected_ifd_bytes, ifd_bytes)

        expected_long_bytes = expected_bytes[offset_software:]
        long_bytes = tiff_img_bytes[offset_software:]
        assert_equals(expected_long_bytes, long_bytes)

