# -*- coding: utf-8 -*-

from io import BytesIO
import struct

from ..binary_format import BinaryFormat
from .tags import TiffTag, TAG_SIZE


__all__ = [
    'adapt_values',
    'bytes_from_tiff_writer',
    'calc_offset',
    'ifd_data',
    'pad_string',
    'print_mismatched_tags',
    'to_bytes',
]

def adapt_values(values, bin_structure):
    """allows to use convenient Python types for fields

    e.g.
        >>> adapt_values({'byte_order': b'II'}, ('byte_order', 'H'))
        {'byte_order': <int>}
    """
    bin_values = {}
    field_specs = dict(bin_structure)
    for name, value in values.items():
        bin_values[name] = _to_int(value, field_specs[name])
    return bin_values

def _to_int(value, format_str):
    if isinstance(value, (int, )):
        return value
    return struct.unpack('<'+format_str, value)

def bytes_from_tiff_writer(tiff_obj):
    buffer = BytesIO()
    tiff_obj.write_bytes(buffer)
    buffer.seek(0)
    return buffer.read()

def calc_offset(nr_tags, long_data=b'', offset=0, img_data=None):
    # excluding TIFF header size because we are only serializing a single
    # TiffImage.
    # 'H' (nr_tags)  -> 2 byte
    # 'i' (next_ifd) -> 4 byte
    IFD_SIZE = 2 + (nr_tags * TAG_SIZE) + 4
    img_size = len(img_data) if (img_data is not None) else 0
    return offset + IFD_SIZE + len(long_data) + img_size

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

def print_mismatched_tags(nr_tags, expected_bytes, tiff_img_bytes, *, verbose=False):
    """Convenience function to help debugging generated TIFF tags in unit tests.

    <expected_bytes> and <tiff_img_bytes> represent a TiffImage (not a TiffFile).
    """
    ifd_offset = 2      # <nr_tags> field
    tag_parser = BinaryFormat(TiffTag.spec)
    for tag_idx in range(nr_tags):
        tag_nr = tag_idx + 1
        offset = tag_idx * TAG_SIZE + ifd_offset
        expected_tag_bytes = expected_bytes[offset:offset + TAG_SIZE]
        expected_tag = tag_parser.parse(expected_tag_bytes)
        actual_tag_bytes = tiff_img_bytes[offset:offset + TAG_SIZE]
        actual_tag = tag_parser.parse(actual_tag_bytes)

        output_prefix = 'Tag %r (#%d): ' % (expected_tag['tag_id'], tag_nr)
        if expected_tag_bytes == actual_tag_bytes:
            if verbose:
                print(output_prefix + 'OK')
            continue
        print(output_prefix + 'BAD')
        print('    expected: %r' % (tuple(expected_tag.items()),))
        print('    actual:   %r' % (tuple(actual_tag.items()),))

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

