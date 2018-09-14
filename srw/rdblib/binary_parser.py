# -*- coding: utf-8 -*-

from collections import OrderedDict
import struct


__all__ = ['BinaryFormat']


class BinaryFormat(object):
    def __init__(self, format_string, field_names, encoding=None):
        self.format_string = format_string
        self.field_names = field_names
        self.encoding = encoding

    @classmethod
    def from_bin_structure(cls, bin_structure):
        format_string = '<'  # little-endian byte ordering
        fields = OrderedDict()
        for name, struc in bin_structure:
            offset = struct.calcsize(format_string)
            fields[name] = offset
            format_string += struc
        field_names = tuple(fields.keys())
        return BinaryFormat(format_string, field_names)

    @property
    def size(self):
        return struct.calcsize(self.format_string)

    def parse(self, binary_data, value_changer=None):
        if self.size != len(binary_data):
            msg_text = 'Size mismatch: record needs %d bytes but input data is %d bytes long'
            raise ValueError(msg_text % (self.size, len(binary_data)))
        raw_values = struct.unpack(self.format_string, binary_data)
        if value_changer:
            raw_values = value_changer(raw_values)
        values = raw_values
        if len(values) != len(self.field_names):
            msg_text = 'record contains %d fields but %d values parsed'
            raise ValueError(msg_text % (len(self.field_names), len(values)))
        name_value_pairs = tuple(zip(self.field_names, values))
        return OrderedDict(name_value_pairs)

    def to_bytes(self, values):
        assert len(self.field_names) == len(values)
        ordered_values = []
        for name in self.field_names:
            ordered_values.append(values[name])
        return struct.pack(self.format_string, *ordered_values)

