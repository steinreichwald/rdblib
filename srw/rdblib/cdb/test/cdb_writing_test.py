# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from .. import cdb_format


class CDBWritingTest(PythonicTestCase):
    def test_can_produce_bytes_for_cdb_field(self):
        field_data = {
            'number': 7,
            'status': 1,
            'name': b'name'  + 16 * b'\x00',
            'rejects': 0,
            'recognizer_result': b'12345' + 35 * b'\x00',
            'corrected_result': b'12345' + 35 * b'\x00',
            'valid': 0,
            'left': 0,
            'top': 0,
            'right': 0,
            'bottom': 0,
        }
        generated_bytes = cdb_format.Field.to_bytes(field_data)
        expected_bytes = (
            b'\x07' + 3 * b'\x00' + \
            b'\x01' + 3 * b'\x00' + \
            field_data['name'] + \
            4 * b'\x00' + \
            field_data['recognizer_result'] + \
            field_data['corrected_result'] + \
            4 * b'\x00' + \
            4 * b'\x00' + \
            4 * b'\x00' + \
            4 * b'\x00' + \
            4 * b'\x00'
        )
        assert_equals(expected_bytes, generated_bytes)

