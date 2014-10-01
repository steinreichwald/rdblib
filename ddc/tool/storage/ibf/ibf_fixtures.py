#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IBF Fixtures can generate IBF binary structures completely in memory for
testing purposes.

Limitations:
Currently we only write a single image entry per index group while real-world
IBF files group images in blocks of 64 entries (see
FormImageBatch.load_directories() for the complete parsing implementation).
"""
from __future__ import division, absolute_import, print_function, unicode_literals

from ddc.dbdef import cdb_definition
from ddc.tool.storage.fixture_helpers import BinaryFixture


__all__ = ['IBFFile', 'IBFImage']

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

    def as_bytes(self, buffer_=None):
        if buffer_ is not None:
            # all offsets are absolute numbers, it would be strange to have some
            # binary junk before the global ibf header
            assert (buffer_.tell() == 0)
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
        buffer_ = super(IBFFile, self).as_bytes(values, buffer_=buffer_)

        # --- writing index entries for all images ----------------------------
        for i, ibf_form_image in enumerate(self.images):
            image_offset = offset_first_image + sum(image_sizes[:i])
            is_last_index = (i + 1 == len(self.images))
            current_offset = buffer_.tell()
            offset_next_index = 0 if is_last_index else (current_offset + index_size)
            ibf_form_image.index_as_bytes(buffer_,
                offset_next_index=offset_next_index,
                image_nr=1,
                image_offset=image_offset
            )

        # --- writing the actual binary image data ----------------------------
        for ibf_form_image in self.images:
            ibf_form_image.img_as_bytes(buffer_)
        return buffer_


class IBFImage(BinaryFixture):
    def __init__(self, img_data, image_nr=None, codenr=None, encoding=None, **values):
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

    def index_as_bytes(self, buffer_, **values):
        values_ = self.values.copy()
        self._assert_caller_used_only_known_fields(values, self.bin_structure)
        values_.update(values)
        buffer_ = super(IBFImage, self).as_bytes(values_, buffer_=buffer_)
        return buffer_

    def img_as_bytes(self, buffer_):
        buffer_.write(self.img_data)
        return buffer_

    def as_bytes(self, buffer_=None, **values):
        raise NotImplementedError('not implemented for IBFImage, please use index_as_bytes() or img_as_bytes()')

