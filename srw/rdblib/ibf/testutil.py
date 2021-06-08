# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os

from ..fixture_helpers import UnclosableBytesIO
from .ibf_fixtures import IBFFile, IBFImage
from ..tiff.testutil import load_tiff_dummy_bytes


__all__ = ['create_ibf']

def create_ibf(nr_images=1, *, pic_nrs=None, filename=None, fake_tiffs=True, create_directory=False):
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

    tiff_data = _fake_tiff_image() if fake_tiffs else load_tiff_dummy_bytes()
    if pic_nrs is None:
        pic_nrs = ('dummy',) * nr_images
    assert nr_images == len(pic_nrs)
    ibf_images = []
    for pic in pic_nrs:
        ibf_img = IBFImage(tiff_data, codnr=pic)
        ibf_images.append(ibf_img)
    # The PIC is also stored inside the actual TIFF image but this code can not
    # generate these data structures currently. So far this was good enough but
    # we might need to extend the functionality later (test stub already
    # prepared).
    ibf_data = IBFFile(ibf_images).as_bytes()
    if filename is None:
        return UnclosableBytesIO(ibf_data)
    ibf_directory = os.path.dirname(filename)
    if create_directory and not os.path.exists(ibf_directory):
        os.makedirs(ibf_directory)
    ibf_fp = open(filename, 'wb+')
    ibf_fp.write(ibf_data)
    ibf_fp.seek(0, 0)
    return ibf_fp

