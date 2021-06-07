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

from .ibf_format import (IBFFormat, BatchHeader, ImageIndexEntry,
    IMAGES_PER_BLOCK, INDEX_PADDING)
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
    tiff_fp = pkg_resources.resource_stream('srw.rdblib.tiff.testutil', 'dummy.tiff')
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
        self._offset_first_index = None
        self.offset_last_index = None

    def as_bytes(self):
        buffer_ = BytesIO()

        index_block_count = math.ceil(len(self.images) / IMAGES_PER_BLOCK)
        assert (index_block_count >= 1) # just to ensure we use float division

        # --- create placeholder for the global header ------------------------
        # At first we just create a placeholder which will be overwritten with
        # the actual data at the end.
        placeholder_batch_header = b'\x00' * BatchHeader.size
        buffer_.write(placeholder_batch_header)

        # --- writing index entries for all images ----------------------------
        self._offset_first_index = None
        self._offset_last_index = None
        # range(1, ...): 1-based counting
        for img_block in range(1, index_block_count+1):
            self._write_index_block(buffer_, img_block, index_block_count)

        # --- writing the global header ---------------------------------------
        # Theoretically we could calculate all the index offsets/the file size
        # before but that was a bit error prone. Instead we just record the
        # offsets and write the batch header once all the index blocks were
        # written.
        file_size = buffer_.tell()
        buffer_.seek(0)
        values = merge_dicts(self.values, {
            'offset_first_index': self._offset_first_index,
            'offset_last_index' : self._offset_last_index,
            'file_size': file_size,
        })
        ibf_data = super(IBFFile, self).as_bytes(values)
        buffer_.write(ibf_data)

        buffer_.seek(0)
        return buffer_.read()


    def _write_index_block(self, buffer_, img_block, index_block_count):
        # An index block consists of:
        #   64x ImageIndexEntry
        #   256 byte padding (0x00)
        #   actual image data
        index_block_size = IMAGES_PER_BLOCK * ImageIndexEntry.size + INDEX_PADDING

        # "-1" because "img_block" is 1-based
        img_idx_start = (img_block - 1) * IMAGES_PER_BLOCK
        img_idx_end = img_block * IMAGES_PER_BLOCK
        imgs_in_block = self.images[img_idx_start:img_idx_end]
        img_sizes_in_block = [img.values['image_size'] for img in imgs_in_block]
        img_count_in_block = len(imgs_in_block)

        block_offset = buffer_.tell()
        if self._offset_first_index is None:
            self._offset_first_index = block_offset
        self._offset_last_index = block_offset
        offset_first_image_in_block = block_offset + (IMAGES_PER_BLOCK * ImageIndexEntry.size) + INDEX_PADDING

        for entry_idx in range(IMAGES_PER_BLOCK):
            img_idx = entry_idx + ((img_block - 1) * IMAGES_PER_BLOCK)
            if img_idx >= len(self.images):
                index_data = b'\x00' * ImageIndexEntry.size
                buffer_.write(index_data)
                continue

            is_first_index = (entry_idx == 0)
            if img_block < index_block_count:
                offset_next_indexblock = block_offset + index_block_size + sum(img_sizes_in_block)
            else:
                offset_next_indexblock = 0
            ibf_form_image = self.images[img_idx]
            image_offset = offset_first_image_in_block + sum(img_sizes_in_block[:entry_idx])

            index_data = ibf_form_image.index_as_bytes(
                is_first_index_entry   = is_first_index,
                offset_next_indexblock = offset_next_indexblock if is_first_index else 0,
                images_in_indexblock   = img_count_in_block if is_first_index else 0,
                image_nr               = (img_idx + 1),
                image_offset           = image_offset,
            )
            buffer_.write(index_data)

        img_pre_padding = b'\x00' * 256
        buffer_.write(img_pre_padding)
        # write actual image data (TIFF)
        for ibf_form_image in imgs_in_block:
            img_data = ibf_form_image.img_as_bytes()
            buffer_.write(img_data)



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

