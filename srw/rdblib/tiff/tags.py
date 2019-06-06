# -*- coding: utf-8 -*-

import struct

from .tag_specification import FieldType, FT, TiffTags
from ..binary_format import BinaryFormat


__all__ = ['TiffTag', 'TAG_SIZE']

class TiffTag:
    def __init__(self, tag_id, tag_value):
        self.tag_id = tag_id
        self.tag_value = tag_value
        self._writer = BinaryFormat(self.spec)

    spec = (
        ('tag_id',            'H'),    # well-known IDs defined in the TIFF specification, see TiffTags
        ('tag_type',          'H'),
        ('nr_values',         'i'),
        ('data',              'i'),    # actual tag value or offset into long block
    )

    @property
    def size(self):
        return self._writer.size

    def to_bytes(self, long_offset=0):
        tag_type = TiffTags[self.tag_id].type
        field_size = FieldType.data_for(tag_type).get('bytes')
        is_len_field = (field_size is len)
        if is_len_field or (field_size > 4):
            nr_values = len(self.tag_value) if is_len_field else 1
            extra_values = ()
            data_or_offset = long_offset
            if tag_type == FT.ASCII:
                long_spec = '%ds' % nr_values
            elif tag_type == FT.RATIONAL:
                long_spec = 'ii'
                # just assume we only have to deal with integers here (denominator = 1)
                extra_values = (1,)
            else:
                raise NotImplementedError('tag_type: %r' % FieldType.constant_for(tag_type))
            long_data = struct.pack('<' + long_spec, self.tag_value, *extra_values)
        else:
            # nr_values = 1 is a simplification which matches our legacy
            # software
            nr_values = 1
            data_or_offset = self.tag_value
            long_data = b''

        tag_attrs = {
            'tag_id': self.tag_id,
            'tag_type': tag_type,
            'nr_values': nr_values,
            'data': data_or_offset,
        }
        return self._writer.to_bytes(tag_attrs), long_data



# 12 bytes
TAG_SIZE = BinaryFormat(TiffTag.spec).size

