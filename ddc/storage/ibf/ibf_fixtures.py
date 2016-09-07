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

import pkg_resources

from ddc.dbdef import cdb_definition
from ddc.storage.fixture_helpers import BinaryFixture, UnclosableBytesIO


__all__ = ['create_ibf', 'IBFFile', 'IBFImage']

def create_ibf(nr_images=1, filename=None, fake_tiffs=True):
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

    def _use_dummy_tiff():
        this_module = __name__.rsplit('.', 1)[0]
        tiff_fp = pkg_resources.resource_stream(this_module, 'dummy.tiff')
        tiff_data = tiff_fp.read()
        return tiff_data

    tiff_data = _fake_tiff_image() if fake_tiffs else _use_dummy_tiff()
    ibf_images = [IBFImage(tiff_data) for i in range(nr_images)]
    ibf_data = IBFFile(ibf_images).as_bytes()
    if filename is None:
        return UnclosableBytesIO(ibf_data)
    ibf_fp = open(filename, 'ab+')
    # seek+truncate just in case the file already exists
    ibf_fp.seek(0, 0)
    ibf_fp.truncate()
    ibf_fp.write(ibf_data)
    ibf_fp.seek(0, 0)
    return ibf_fp


ibf_format = cdb_definition.Image_Defn

class IBFFile(BinaryFixture):
    def __init__(self, images, encoding=None):
        self.images = images
        values = dict(
            identifier='WIBF',
            _ign1=1,
            _ign2=1,
            filename='',
            scan_date='',
            # offset_first_index=252  (calculated in as_bytes())
            # offset_last_index (calculated in as_bytes())
            image_count=len(images),
            # file_size (calculated in as_bytes())
            _ign3='',
        )
        bin_structure = ibf_format.header_struc
        super(IBFFile, self).__init__(values, bin_structure, encoding=encoding)

    def as_bytes(self):
        buffer_ = BytesIO()
        header_size = 252 # size of ibf_format.header_struc
        index_size = 256
        max_index = self.values['image_count'] - 1
        image_sizes = [img.values['image_size'] for img in self.images]

        # --- serializing the global header -----------------------------------
        offset_first_index = header_size
        offset_last_index = offset_first_index + (max_index * index_size)
        offset_first_image = offset_last_index + index_size
        file_size = offset_first_image + sum(image_sizes)

        values = self.values.copy()
        values.update(
            offset_first_index=offset_first_index,
            offset_last_index=offset_last_index,
            file_size=file_size,
        )
        ibf_data = super(IBFFile, self).as_bytes(values)
        buffer_.write(ibf_data)

        # --- writing index entries for all images ----------------------------
        for i, ibf_form_image in enumerate(self.images):
            image_offset = offset_first_image + sum(image_sizes[:i])
            is_last_index = (i + 1 == len(self.images))
            current_offset = buffer_.tell()
            offset_next_index = 0 if is_last_index else (current_offset + index_size)
            index_data = ibf_form_image.index_as_bytes(
                offset_next_index=offset_next_index,
                image_nr=1,
                image_offset=image_offset
            )
            buffer_.write(index_data)

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
            first_index_entry=0,
            _ign1=0,                   # _ign1
            # offset_next_index (calculated in as_bytes())
            offset_next_index=0,
            indexblock_len=1,
            _ign2=1,                   # _ign2
            image_nr=image_nr,
            # image_offset (calculated in as_bytes())
            image_size=len(img_data),
            identifier='REZEPT',
            codnr='',
        )
        values_.update(values)
        bin_structure = ibf_format.index_struc
        super(IBFImage, self).__init__(values_, bin_structure, encoding=encoding)

    def index_as_bytes(self, **values):
        values_ = self.values.copy()
        values_.update(values)
        self._assert_caller_used_only_known_fields(values, self.bin_structure)
        index_data = super(IBFImage, self).as_bytes(values_)
        return index_data

    def img_as_bytes(self):
        return self.img_data

    def as_bytes(self, **values):
        raise NotImplementedError('not implemented for IBFImage, please use index_as_bytes() or img_as_bytes()')
