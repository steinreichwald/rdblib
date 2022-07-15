
from io import BytesIO
import os

from PIL import Image

from ..lib import PIC
from .tag_specification import TIFF_TAG as TT


__all__ = ['pic_str_from_tiff', 'pic_from_tiff']

def pic_str_from_tiff(tiff_path_or_bytes, *, strip=True):
    pillow_img = _build_pillow_img_from_data(tiff_path_or_bytes)

    img1_tags = dict(pillow_img.tag_v2.items())
    pic_str_img1 = img1_tags.get(TT.PageName)
    pillow_img.seek(1)
    img2_tags = dict(pillow_img.tag_v2.items())
    pic_str_img2 = img2_tags.get(TT.PageName)
    # no need to explicitely ".close()" the "pillow_img" as
    # "_build_pillow_img_from_data()" does not pass a path to "Image.open()"
    # hence the pillow image does not reference a real file on disk directly.
    #
    # This is important because otherwise the code would leave file handles
    # open and that would lead to unpleasant suprises on Windows.
    assert pic_str_img1 == pic_str_img2

    raw_pic_str = pic_str_img2
    pic_str = raw_pic_str.rstrip('\x00') if strip else raw_pic_str
    return pic_str

def pic_from_tiff(tiff_path_or_bytes, *, strip=True):
    pic_str = pic_str_from_tiff(tiff_path_or_bytes, strip=strip)
    return PIC.from_str(pic_str)

def is_pillow_img(obj):
    # same check as pillow's isImageType()
    return hasattr(obj, 'im')

def _build_pillow_img_from_data(path_or_bytes):
    if is_pillow_img(path_or_bytes):
        pillow_img = path_or_bytes
        return pillow_img

    tiff_fp = None
    if isinstance(path_or_bytes, (str, os.PathLike)):
        tiff_path = path_or_bytes
        # Read the complete file into memory. This simplifies the code below
        # but more importantly it ensures "Image.open()" does not reference
        # a real file on disk directly.
        # This is important because we should be careful not to leave open
        # file handles hanging around which could lead to unpleasant suprises
        # on Windows.
        with open(tiff_path, 'rb') as fp:
            tiff_fp = BytesIO(fp.read())
    elif isinstance(path_or_bytes, bytes):
        tiff_fp = BytesIO(path_or_bytes)
    else:
        assert hasattr(path_or_bytes, 'read')
        tiff_fp = path_or_bytes
    return Image.open(tiff_fp)

