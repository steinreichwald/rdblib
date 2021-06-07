
from collections import namedtuple

from PIL import Image

from .tag_specification import TIFF_TAG as TT
from srw.rdblib.utils import pad_bytes


__all__ = ['get_tiff_img_data', 'pad_tiff_bytes']

def pad_tiff_bytes(value, length):
    data = b''
    if isinstance(value, str):
        # TIFF specification (page 15): "8-bit byte that contains a 7-bit ASCII code"
        data = value.encode('ASCII')
    else:
        data += value
    padded_data = pad_bytes(data, length=length, pad_right=True, pad_byte=b'\x00')
    # TIFF specification (page 15): "the last byte must be NUL (binary zero)"
    assert (padded_data[-1:] == b'\x00')
    return padded_data


def get_tiff_img_data(tiff_path):
    """Return the actual tiff image data (without tiff tags and other tiff
    metadata for a given 2-page tiff file with tags)."""
    with tiff_path.open('rb') as tiff_fp:
        tiff_bytes = tiff_fp.read()

    _data = []
    with Image.open(str(tiff_path)) as tiff_img:
        _data1 = _tiff_img_data(tiff_img, tiff_bytes)
        _data.append(_data1)
        tiff_img.seek(1)
        _data2 = _tiff_img_data(tiff_img, tiff_bytes)
        _data.append(_data2)
    return _data


TiffData = namedtuple('TiffData', ('width', 'height', 'img_data'))

def _tiff_img_data(tiff_img, tiff_bytes):
    tags1 = dict(zip(tiff_img.tag_v2.keys(), tiff_img.tag_v2.values()))
    img_offset = tags1[TT.StripOffsets][0]
    size = tags1[TT.StripByteCounts][0]

    width = tags1[TT.ImageWidth]
    height = tags1[TT.ImageLength]
    img_data = tiff_bytes[img_offset:img_offset + size]
    return TiffData(width, height, img_data)

