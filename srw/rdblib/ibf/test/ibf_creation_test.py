# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from srw.rdblib.binary_format import BinaryFormat
from ..ibf_fixtures import dummy_tiff_data, IBFFile, IBFImage
from ..ibf_format import IBFFormat
from srw.rdblib.testutil import colorized_diff
from srw.rdblib.utils import pad_bytes


class IBFCreationTest(PythonicTestCase):
    def test_can_generate_ibf_file_with_single_scan(self):
        ibf_filename = '12345678.IBF'
        scan_date = '12.02.2020'
        tiff_data = dummy_tiff_data()

        # we need 2 images to test the "offset_last_index" properly
        ibf_image1 = IBFImage(tiff_data, codnr='01265400123024')
        ibf_image2 = IBFImage(tiff_data, codnr='01265400124024')
        ibf_images = [ibf_image1, ibf_image2]
        ibf_batch = IBFFile(ibf_images, ibf_filename=ibf_filename, scan_date=scan_date)
        generated_ibf = ibf_batch.as_bytes()

        batch_header = BinaryFormat(IBFFormat.batch_header)
        IndexEntry = BinaryFormat(IBFFormat.index_entry)

        padding = b'\x00' * 256
        batch_header_values = adapt_values(IBFFormat.batch_header, {
            'identifier' : 'WIBF',
            '_ign1'      : 1,
            '_ign2'      : 1,
            'filename'   : ibf_filename,
            'scan_date'  : scan_date,
            'offset_first_index': batch_header.size,
            'offset_last_index' : batch_header.size,
            'image_count': 2,
            'file_size'  : batch_header.size + (64 * IndexEntry.size) + len(padding) + 2 * len(tiff_data),
            '_ign3'      : '',
        })
        expected_header = batch_header.to_bytes(batch_header_values)
        generated_header = generated_ibf[:batch_header.size]
        if generated_header != expected_header:
            colorized_diff(expected_header, generated_header)
        assert_equals(expected_header, generated_ibf[:batch_header.size])


        # -- testing the index header --
        offset_img1 = batch_header.size + (64 * IndexEntry.size) + 256
        index1_values = adapt_values(IBFFormat.index_entry, {
            'is_first_index_entry'  : 1,
            '_ign1'       : 0,
            'offset_next_indexblock': 0,
            'images_in_indexblock'  : 2,
            '_ign2'       : 1,
            '_ign3'       : 0,
            'image_nr'    : 1,
            'image_offset': offset_img1,
            'image_size'  : len(tiff_data),
            'identifier'  : pad_bytes(b'REZEPT', length=80, pad_byte=b'\x00'),
            'codnr'       : pad_bytes(b'01265400123024', length=140, pad_byte=b'\x00'),
        })
        index_start = batch_header.size
        index1_end = index_start + IndexEntry.size
        expected_index1 = IndexEntry.to_bytes(index1_values)
        generated_index1 = generated_ibf[index_start:index1_end]
        if generated_index1 != expected_index1:
            colorized_diff(expected_index1, generated_index1)
        assert_equals(expected_index1, generated_index1)

        offset_img2 = offset_img1 + len(tiff_data)
        index2_values = adapt_values(IBFFormat.index_entry, {
            'is_first_index_entry'  : 0,
            '_ign1'       : 0,
            'offset_next_indexblock': 0,
            'images_in_indexblock'  : 0,
            '_ign2'       : 1,
            '_ign3'       : 0,
            'image_nr'    : 2,
            'image_offset': offset_img2,
            'image_size'  : len(tiff_data),
            'identifier'  : pad_bytes(b'REZEPT', length=80, pad_byte=b'\x00'),
            'codnr'       : pad_bytes(b'01265400124024', length=140, pad_byte=b'\x00'),
        })
        index_start = index1_end
        index2_end = index_start + IndexEntry.size
        expected_index2 = IndexEntry.to_bytes(index2_values)
        generated_index2 = generated_ibf[index_start:index2_end]
        if generated_index2 != expected_index2:
            colorized_diff(expected_index2, generated_index2)
        assert_equals(expected_index2, generated_index2)

        # remaining index block (62 entries) should be empty
        empty_index_entries = b'\x00' * ((64 - 2) * IndexEntry.size)
        offset_index_block_end = batch_header.size + (64 * IndexEntry.size)
        generated_index_entries = generated_ibf[index2_end:offset_index_block_end]
        assert_equals(empty_index_entries, generated_index_entries)

        # --- check padding after index block / before tiff images ---
        offset_padding_start = offset_index_block_end
        offset_padding_end = offset_padding_start + 256
        generated_padding = generated_ibf[offset_padding_start:offset_padding_end]
        assert_equals(padding, generated_padding)

        # --- check tiff images ---
        assert_equals(offset_img1, offset_padding_end,
            message='ensure we did not miscalcuate badly/enforce consistency')
        # second slice: relative offset
        ibf_tiff1 = generated_ibf[offset_img1:][:len(tiff_data)]
        assert_equals(tiff_data, ibf_tiff1)

        ibf_tiff2 = generated_ibf[offset_img2:][:len(tiff_data)]
        assert_equals(tiff_data, ibf_tiff2)



def adapt_values(bin_structure, values):
    """allows to use convenient Python types for fields, adds missing fields
    """
    user_values = dict(values)
    bin_values = {}
    field_specs = dict(bin_structure)
    for field_name, field_spec in field_specs.items():
        if field_name not in user_values:
            value = 0
        else:
            value = user_values.pop(field_name)
            if isinstance(value, str):
                value = value.encode('ASCII')

        bin_values[field_name] = value
    assert len(user_values) == 0, user_values
    return bin_values

