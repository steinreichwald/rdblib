# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import OrderedDict

from ..binary_parser import BinaryFormat


__all__ = ['BatchHeader', 'CDBFormat', 'CDB_ENCODING', 'FormHeader', 'Field']

CDB_ENCODING = 'cp850'

class CDBFormat(object):
    batch_header = (
        ('ibf_path',          '128s'),
        ('ibf_format_string', '16s'),
        ('form_count',        'i'),
        ('next_form',         'i'),
        ('recognized_forms',  'i'),
    )

    form_header = (
        ('number_in_batch',    'i'),
        ('status',             'i'),
        ('imprint_line_short', '20s'),
        ('field_count',        'i'),
        ('pharmacy_rejects',   'i'),
        ('doctor_rejects',     'i'),
        ('_valid',              'i'),
        ('left_margin',        'i'),
        ('top_margin',         'i'),
        ('right_margin',       'i'),
        ('bottom_margin',      'i'),
        ('rear_side',          'i'),
        ('imprint_line_long',  '80s'),
        ('_ign1',              '16s'), # ''
    )

    field = (
        ('number',            'i'),
        ('status',            'i'),
        ('name',              '20s'),
        ('rejects',           'i'),
        ('recognizer_result', '40s'),
        ('corrected_result',  '40s'),
        ('_valid',             'i'),
        ('left',              'i'),
        ('top',               'i'),
        ('right',             'i'),
        ('bottom',            'i'),
    )

    @classmethod
    def batch_headers(cls):
        return _attributes(cls.batch_header)

    @classmethod
    def batch_header_formatstring(cls):
        return _format_string(cls.batch_headers())

    @classmethod
    def form_headers(cls):
        return _attributes(cls.form_header)

    @classmethod
    def form_header_formatstring(cls):
        return _format_string(cls.form_headers())

    @classmethod
    def field_attributes(cls):
        return _attributes(cls.field)

    @classmethod
    def field_formatstring(cls):
        return _format_string(cls.field_attributes())

BatchHeader = BinaryFormat.from_bin_structure(CDBFormat.batch_header)
FormHeader = BinaryFormat.from_bin_structure(CDBFormat.form_header)
Field = BinaryFormat.from_bin_structure(CDBFormat.field)


def _attributes(definitions):
    headers = OrderedDict()
    for key, fmt in definitions:
        headers[key] = fmt
    return headers

def _format_string(attrs):
        return ''.join(attrs.values())

