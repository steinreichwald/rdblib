
from collections import namedtuple
from io import BytesIO

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


def get_tiff_img_data(tiff_path_or_fp):
    """Return the actual tiff image data (without tiff tags and other tiff
    metadata for a given 2-page tiff file with tags)."""
    if hasattr(tiff_path_or_fp, 'read'):
        tiff_fp = tiff_path_or_fp
        tiff_bytes = tiff_fp.read()
        tiff_fp.seek(0)
    else:
        tiff_path = tiff_path_or_fp
        with tiff_path.open('rb') as tiff_fp:
            tiff_bytes = tiff_fp.read()
        tiff_fp = BytesIO(tiff_bytes)

    _data = []
    with Image.open(tiff_fp) as tiff_img:
        img_count = tiff_img.n_frames
        for img_idx in range(img_count):
            tiff_img.seek(img_idx)
            _tiff_data = _tiff_img_data(tiff_img, tiff_bytes)
            _data.append(_tiff_data)

    if len(_data) == 1:
        return _data[0]
    return _data


TiffData = namedtuple('TiffData', ('width', 'height', 'img_data'))

def _tiff_img_data(tiff_img, tiff_bytes):
    tags = dict(zip(tiff_img.tag_v2.keys(), tiff_img.tag_v2.values()))
    strip_offsets = tags[TT.StripOffsets]
    assert len(strip_offsets) == 1
    img_offset, = strip_offsets
    strip_byte_counts = tags[TT.StripByteCounts]
    assert len(strip_byte_counts) == 1
    size, = strip_byte_counts

    width = tags[TT.ImageWidth]
    height = tags[TT.ImageLength]
    img_data = tiff_bytes[img_offset:img_offset + size]
    return TiffData(width, height, img_data)

