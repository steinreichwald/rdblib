# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals


from ..binary_parser import BinaryFormat

__all__ = [
    'BatchHeader',
    'IBFFormat',
    'ImageIndexEntry',
    'IMAGES_PER_BLOCK',
    'INDEX_PADDING',
    'Tiff',
]

# Eine IBF-Datei ist wie folgt aufgebaut:
#
#   globaler Batch-Header
#   [1-5 Blöcke mit bis zu 64 Images]
#
# Jeder "Block" besteht aus:
#   64 IndexEntries
#   die tatsächlichen TIFF-Bilddaten
#   256 Byte Padding (0-Bytes)
# Falls es weniger Belege als 64 im Block gibt, werden die restlichen
# IndexEntries mit 0-Bytes belegt. Bei den TIFF-Bilddaten gibt es aber keine
# Platzhalter.
#
# Die "IndexEntries" sind eine Art "Inhaltsverzeichnis", so dass man z.B. die
# Bilddaten für eine bestimmte PIC-Nummer abrufen kann, ohne Annahmen über das
# TIFF-Format machen zu müssen.
#
# Grundidee der IBF-Datei ist es wohl, diese Datei beim Scannen kontinuierlich
# schreiben zu können, ohne die gesamten Daten im Arbeitsspeicher halten zu
# müssen.

IMAGES_PER_BLOCK = 64
INDEX_PADDING = 256

# This class describes the proprietary IBF format (excluding the actual TIFF
# data even though that is also included within the IBF file).
class IBFFormat(object):
    batch_header = (
        ('identifier',         '4s'),  # 'WIBF'
        ('_ign1',              'i'),   # =1 (statisch)
        ('_ign2',              'i'),   # =1 (statisch)
        ('filename',           '16s'), # '12345678.IBF' + 0x00 termination/padding
        ('scan_date',          '12s'), # 'DD.MM.JJJJ' + 0x00 termination/padding
        ('offset_first_index', 'i'),
        ('offset_last_index',  'i'),   # *starting* offset of the last index
        ('image_count',        'i'),
        ('file_size',          'i'),
        ('_ign3',              '196s'), # ''
    )

    index_entry = (
        ('is_first_index_entry',   'i'), # =1, wenn es der erste Eintrag in einem Index-Verzeichnis mit 64 Rezepten ist
        ('_ign1',                  'i'), # =0 (statisch)
        ('offset_next_indexblock', 'i'), # nur im ersten Index-Eintrag jedes Index-Blocks belegt (sonst 0)
        ('images_in_indexblock',   'i'), # Anzahl der Images in diesem Index-Verzeichnis (nur bei erstem Eintrag)
        ('_ign2',                  'i'), # =1 (statisch)
        ('_ign3',                  'i'), # =0 (statisch)
        ('image_nr',               'i'), # Nummer des Images innerhalb der IBF-Datei
        ('image_offset',           'i'), # points to tiff header
        ('image_size',             'i'),
        ('identifier',           '80s'), # 'REZEPT' + 0x00 termination/padding
        ('codnr',               '140s'), # 14 used + 0x00 termination/padding
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
        # size to here == 496
    )


BatchHeader = BinaryFormat.from_bin_structure(IBFFormat.batch_header)
ImageIndexEntry = BinaryFormat.from_bin_structure(IBFFormat.index_entry)
# no parsers for Tiff class - we don't use these currently
