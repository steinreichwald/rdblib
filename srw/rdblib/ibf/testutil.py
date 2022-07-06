# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from pathlib import Path

from ..fixture_helpers import UnclosableBytesIO
from .ibf_fixtures import IBFFile, IBFImage
from ..tiff import pic_str_from_tiff
from ..tiff.testutil import load_tiff_dummy_bytes


__all__ = ['create_ibf', 'create_ibf_with_tiffs']

def create_ibf_with_tiffs(tiffs, *, ibf_path=None, create_directory=False):
    ibf_images = []
    for tiff in tiffs:
        if isinstance(tiff, (tuple, list)):
            pic_str, tiff_bytes = tiff
        else:
            tiff_bytes = tiff
            pic_str = pic_str_from_tiff(tiff_bytes)
        ibf_img = IBFImage(tiff_bytes, codnr=pic_str)
        ibf_images.append(ibf_img)

    ibf_data = IBFFile(ibf_images).as_bytes()
    if ibf_path is None:
        return UnclosableBytesIO(ibf_data)

    ibf_path = Path(ibf_path)
    ibf_directory = ibf_path.parent
    if create_directory and not ibf_directory.exists():
        ibf_directory.mkdir(parents=True, exist_ok=True)
    ibf_fp = ibf_path.open('wb+')
    ibf_fp.write(ibf_data)
    ibf_fp.seek(0, 0)
    return ibf_fp

def create_ibf(nr_images=1, *, pic_nrs=None, filename=None, fake_tiffs=True, create_directory=False):
    img_count = nr_images
    pic_strs = pic_nrs
    # tiffany can not create tiff images and I'd like not to add new
    # dependencies (smc.freeimage needs compilation and has a few extra
    # dependencies, PIL can't handle multi-page tiffs).
    # Current tests don't need actual tiffs so we can just use some random
    # binary data.
    # However some scripts need to provide real tiffs so we have a static dummy
    # tiff which is used if fake_tiffs is False.
    # (Also Pillow should be able to handle multi-page tiffs so that might be
    # good thing to explore - we'd be able to replace tiffany with the much
    # more common Pillow).
    def _fake_tiff_image():
        return b'\x00' * 200

    if pic_strs is None:
        pic_strs = ('dummy',) * img_count
    assert img_count == len(pic_strs)
    tiffs = []
    # The PIC is also stored inside the actual TIFF image but this code can not
    # generate these data structures currently. So far this was good enough but
    # we might need to extend the functionality later (test stub already
    # prepared).
    for pic_str in pic_strs:
        if fake_tiffs:
            tiff_bytes = _fake_tiff_image()
        else:
            tiff_bytes = load_tiff_dummy_bytes(pic_str=pic_str)
        tiffs.append((pic_str, tiff_bytes))
    ibf_path = Path(filename) if filename else None
    return create_ibf_with_tiffs(tiffs, ibf_path=ibf_path, create_directory=create_directory)

