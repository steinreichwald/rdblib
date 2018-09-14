# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals


from ..binary_parser import BinaryFormat

__all__ = [
    'BatchHeader',
    'IBFFormat',
    'ImageIndexEntry',
    'Tiff',
]

# This class describes the proprietary IBF format (excluding the actual TIFF
# data even though that is also included within the IBF file).
class IBFFormat(object):
    batch_header = (
        ('identifier',         '4s'), # 'WIBF'
        ('_ign1',              'i'),
        ('_ign2',              'i'),
        ('filename',           '16s'),
        ('scan_date',          '12s'),
        ('offset_first_index', 'i'),
        ('offset_last_index',  'i'),
        ('image_count',        'i'),
        ('file_size',          'i'),
        ('_ign3',              '196s'), # ''
    )

    index_entry = (
        ('first_index_entry', 'i'),
        ('_ign1',             'i'),
        ('offset_next_index', 'i'),
        ('indexblock_len',    'i'),
        ('_ign2',             'i'),
        ('_ign3',             'i'),
        ('image_nr',          'i'),
        ('image_offset',      'i'),    # points to tiff header
        ('image_size',        'i'),
        ('identifier',        '80s'),  # 'REZEPT'
        ('codnr',             '140s'), # 14 used
    )


# This describes the actual TIFF data.
class Tiff(object):
    header = (
        ('byte_order',        'H'),    # in IBF always 'II' = Intel
        ('version',           'H'),    # always 42 for TIFF
        ('first_ifd',         'i'),    # in IBF always 8
        # size to here == 8
    )

    ifd = (
        ('num_tags',          'H'),    # in IBF always 27
        ('tag_block',         '324s'), # tag size = 12 -> 324
        ('next_ifd',          'i'),    # offset of next ifd or 0
    )

    tag = (
        ('tag_id',            'H'),
        ('tag_type',          'H'),
        ('num_of_values',     'i'),
        ('data_or_offset',    'i'),
    )

    # the following comes right after the IFD
    long_data = (
        ('xresolution',       'i'),
        ('xres_denom',        'i'),  # 1
        ('yresolution',       'i'),
        ('yres_denom',        'i'),  # 1
        ('document_name',     '80s'),
        ('image_description', '20s'),
        ('make',              '40s'),
        ('model',             '40s'),
        ('page_name',         '80s'), # 30330200002024
        ('software',          '40s'),
        ('datetime',          '20s'),
        ('artist',            '80s'),
        ('host_computer',     '80s'),
        # site to here == 496
    )


BatchHeader = BinaryFormat.from_bin_structure(IBFFormat.batch_header)
ImageIndexEntry = BinaryFormat.from_bin_structure(IBFFormat.index_entry)
# no parsers for Tiff class - we don't use these currently
