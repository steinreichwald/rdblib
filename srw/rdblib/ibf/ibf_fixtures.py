# -*- coding: utf-8 -*-
"""
IBF Fixtures can generate IBF binary structures completely in memory for
testing purposes.

Limitations:
Currently we only write a single image entry per index group while real-world
IBF files group images in blocks of 64 entries (see
ImageBatch.load_directories() for the complete parsing implementation).
"""
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import math
import os

import pkg_resources

from .ibf_format import IBFFormat, BatchHeader, ImageIndexEntry
from ..fixture_helpers import BinaryFixture, UnclosableBytesIO
from srw.rdblib.lib import merge_dicts


__all__ = ['create_ibf', 'dummy_tiff_data', 'IBFFile', 'IBFImage']

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

    tiff_data = _fake_tiff_image() if fake_tiffs else dummy_tiff_data()
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


def dummy_tiff_data():
    this_module = __name__.rsplit('.', 1)[0]
    tiff_fp = pkg_resources.resource_stream(this_module, 'dummy.tiff')
    tiff_data = tiff_fp.read()
    return tiff_data


class IBFFile(BinaryFixture):
    def __init__(self, images, encoding=None, ibf_filename='', scan_date=''):
        self.images = images
        values = dict(
            identifier='WIBF',
            _ign1=1,
            _ign2=1,
            filename    = ibf_filename,
            scan_date   = scan_date,
            # offset_first_index=252  (calculated in as_bytes())
            # offset_last_index (calculated in as_bytes())
            image_count=len(images),
            # file_size (calculated in as_bytes())
            _ign3='',
        )
        bin_structure = IBFFormat.batch_header
        super(IBFFile, self).__init__(values, bin_structure, encoding=encoding)

    def as_bytes(self):
        buffer_ = BytesIO()
        index_size = ImageIndexEntry.size
        image_sizes = [img.values['image_size'] for img in self.images]

        imgs_per_block = 64
        index_block_size = imgs_per_block * index_size
        index_padding = 256
        index_block_count = math.ceil(len(self.images) / imgs_per_block)
        assert (index_block_count >= 1) # just to ensure we use float division
        assert (index_block_count == 1), 'multiple indexes not yet implemented'

        # --- serializing the global header -----------------------------------
        offset_first_index = BatchHeader.size
        # "-1" because "offset_last_index" contains the *starting* positing of
        # the last index
        offset_last_index = offset_first_index + ((index_block_count - 1) * index_size)
        offset_first_image = BatchHeader.size + (index_block_count * index_block_size) + index_padding
        file_size = offset_first_image + sum(image_sizes)

        values = merge_dicts(self.values, {
            'offset_first_index': offset_first_index,
            'offset_last_index' : offset_last_index,
            'file_size': file_size,
        })
        ibf_data = super(IBFFile, self).as_bytes(values)
        buffer_.write(ibf_data)

        # --- writing index entries for all images ----------------------------
        images_in_indexblock = len(self.images)
        img_block = 1
        for block_idx in range(imgs_per_block):
            img_idx = block_idx + ((img_block - 1) * imgs_per_block)
            if img_idx >= len(self.images):
                index_data = b'\x00' * index_size
                buffer_.write(index_data)
                continue

            is_first_index = (block_idx == 0)
            if img_block < index_block_count:
                offset_next_indexblock = BatchHeader.size + (img_block * index_block_size)
            else:
                offset_next_indexblock = 0
            ibf_form_image = self.images[img_idx]
            image_offset = offset_first_image + sum(image_sizes[:img_idx])

            index_data = ibf_form_image.index_as_bytes(
                is_first_index_entry   = is_first_index,
                offset_next_indexblock = offset_next_indexblock,
                images_in_indexblock   = images_in_indexblock if is_first_index else 0,
                image_nr               = (img_idx + 1),
                image_offset           = image_offset,
            )
            buffer_.write(index_data)

        img_pre_padding = b'\x00' * 256
        buffer_.write(img_pre_padding)

        # --- writing the actual binary image data ----------------------------
        for ibf_form_image in self.images:
            img_data = ibf_form_image.img_as_bytes()
            buffer_.write(img_data)
        buffer_.seek(0)
        return buffer_.read()


class IBFImage(BinaryFixture):
    def __init__(self, img_data, image_nr=None, encoding=None, **values):
        self.img_data = img_data
        values_ = dict(
            is_first_index_entry   = 0,
            _ign1      = 0,
            # offset_next_indexblock (calculated in as_bytes())
            offset_next_indexblock = 0,
            images_in_indexblock   = 1,
            _ign2      = 1,
            image_nr   = image_nr,
            # image_offset (calculated in as_bytes())
            image_size = len(img_data),
            identifier = 'REZEPT',
            codnr      = '',
        )
        values_.update(values)
        bin_structure = IBFFormat.index_entry
        super(IBFImage, self).__init__(values_, bin_structure, encoding=encoding)

    def index_as_bytes(self, **values):
        values_ = merge_dicts(self.values, values)
        self._assert_caller_used_only_known_fields(values, self.bin_structure)
        index_data = super(IBFImage, self).as_bytes(values_)
        return index_data

    def img_as_bytes(self):
        return self.img_data

    def as_bytes(self, **values):
        raise NotImplementedError('not implemented for IBFImage, please use index_as_bytes() or img_as_bytes()')

