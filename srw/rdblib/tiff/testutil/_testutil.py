# -*- coding: utf-8 -*-

from collections import namedtuple
from pathlib import Path
import struct

from srw.rdblib.binary_format import BinaryFormat
from ..tag_specification import FT, TIFF_TAG as TT
from ..tags import TiffTag, TAG_SIZE
from ..tiff_util import get_tiff_img_data
from ..walther_tiff import inject_pic_in_tiff


__all__ = [
    'adapt_values',
    'blend_in_tiff_dummy',
    'calc_offset',
    'ifd_data',
    'load_tiff_dummy_bytes',
    'load_tiff_dummy_img',
    'padding',
    'path_dummy_tiff',
    'print_mismatched_tags',
    'star_extract',
    'tag_StripByteCounts',
    'tag_StripOffsets',
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

def calc_offset(nr_tags, long_data=b'', offset=0, *, padding=False, img_data=None):
    # excluding TIFF header size because we are only serializing a single
    # TiffImage.
    # 'H' (nr_tags)  -> 2 byte
    # 'i' (next_ifd) -> 4 byte
    IFD_SIZE = 2 + (nr_tags * TAG_SIZE) + 4
    final_offset = offset + IFD_SIZE + len(long_data)
    if padding or (img_data is not None):
        # legacy TIFF library always uses a fixed 6 byte padding (even though
        # the TIFF specification mandates word-aligned offsets).
        nr_pad_bytes = 6
        final_offset += nr_pad_bytes
    if img_data:
        img_size = len(img_data)
        final_offset += img_size
    return final_offset

def ifd_data(nr_tags, tag_data, long_data=None):
    tag_data = to_bytes(tag_data)
    ifd_header = to_bytes((
        ('H', nr_tags),
        ('%ds' % (nr_tags * TAG_SIZE), tag_data), # tag_data
        ('i', 0),       # next_ifd
    ))
    return ifd_header + (long_data or b'')


def path_dummy_tiff():
    rdblib_tiff_path = Path(__file__).parent
    tiff_data_path = rdblib_tiff_path / 'dummy.tiff'
    return tiff_data_path.resolve()

# support for pyfakefs
def blend_in_tiff_dummy(fs):
    tiff_path_str = str(path_dummy_tiff())
    fs.add_real_file(tiff_path_str)

def load_tiff_dummy_bytes(*, pic_str=None):
    tiff_path = path_dummy_tiff()
    if pic_str:
        return inject_pic_in_tiff(tiff_path, pic_str)
    with tiff_path.open('rb') as tiff_fp:
        tiff_bytes = tiff_fp.read()
    return tiff_bytes


ImgInfo = namedtuple('ImgInfo', ('data', 'tags', 'size'))

def load_tiff_dummy_img(page=None, all_pages=None):
    if (page is None) and (all_pages is None):
        page = 1
    else:
        assert bool(page) ^ all_pages
    if not all_pages:
        assert (page in (1, 2))
    pages = [page] if (not all_pages) else [1, 2]

    tiff_path = path_dummy_tiff()
    data1, data2 = get_tiff_img_data(tiff_path)

    img_infos = []
    for page in pages:
        tiff_data = data1 if (page == 1) else data2
        width = tiff_data.width
        height = tiff_data.height
        _tiff_tags = {
            TT.ImageWidth : width,
            TT.ImageLength: height,
            TT.Compression: 4,      # Compression ("Group 4 Fax")
            262           : 0,      # PhotometricInterpretation ("WhiteIsZero")
        }
        img_infos.append(
            ImgInfo(tiff_data.img_data, _tiff_tags, (width, height))
        )
    if all_pages:
        return img_infos
    return img_infos[0]

def padding(nr_bytes):
    return nr_bytes * b'\x00'

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


def star_extract(*args):
    """Python >= 3.5 supports a handy syntax: foo = (1, 2, *_bar(), 4, 5)
    This syntax was introduced in PEP 448 (Python 3.5).

    This function implements a workaround for Python 3.3/3.4 so we can use
    almost the same code and churn will be minimal once we can drop support
    for Python < 3.5.
    """
    output = []
    for arg in args:
        if len(arg) == 2:
            output.append(arg)
        else:
            for star_arg in arg:
                output.append(star_arg)
    return tuple(output)

def tag_StripByteCounts(img_data):
    # 279: StripByteCounts
    tag_spec = (('H', 279), ('H', FT.LONG), ('i', 1), ('i', len(img_data)))
    return tag_spec

def tag_StripOffsets(nr_tags, expected_long_data=b'', offset=0):
    offset_to_image = calc_offset(nr_tags, expected_long_data, offset=offset, padding=True)
    # 273: StripOffsets
    tag_spec = (('H', 273), ('H', FT.LONG), ('i', 1), ('i', offset_to_image))
    return tag_spec


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

