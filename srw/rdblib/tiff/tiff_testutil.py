# -*- coding: utf-8 -*-

import struct

from .tags import TAG_SIZE


__all__ = [
    'calc_offset',
    'ifd_data',
    'pad_string',
    'tiff_image_to_bytes',
    'to_bytes',
]

def calc_offset(nr_tags, long_data=b'', img_data=None):
    # excluding TIFF header size because we are only serializing a single
    # TiffImage.
    # 'H' (nr_tags)  -> 2 byte
    # 'i' (next_ifd) -> 4 byte
    IFD_SIZE = 2 + (nr_tags * TAG_SIZE) + 4
    img_size = len(img_data) if (img_data is not None) else 0
    return IFD_SIZE + len(long_data) + img_size

def ifd_data(nr_tags, tag_data, long_data=None):
    tag_data = to_bytes(tag_data)
    ifd_header = to_bytes((
        ('H', nr_tags),
        ('%ds' % (nr_tags * TAG_SIZE), tag_data), # tag_data
        ('i', 0),       # next_ifd
    ))
    return ifd_header + (long_data or b'')

def pad_string(string, length):
    data = b''
    if isinstance(string, str):
        # TIFF specification (page 15): "8-bit byte that contains a 7-bit ASCII code"
        data = string.encode('ASCII')
    else:
        data += string
    # TIFF specification (page 15): "the last byte must be NUL (binary zero)"
    if not data.endswith(b'\x00'):
        data += b'\x00'
    if len(data) < length:
        nr_fill_bytes = length - len(data)
        data += (b'\x00' * nr_fill_bytes)
    return data

def to_bytes(data):
    formats, data_values = _split_pairs(data)
    format_string = '<' + ''.join(formats)
    return struct.pack(format_string, *data_values)

def _split_pairs(value_pairs):
    a = []
    b = []
    for pair in value_pairs:
        first, second = pair
        a.append(first)
        b.append(second)
    return a, b

