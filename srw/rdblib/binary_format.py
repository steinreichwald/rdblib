# -*- coding: utf-8 -*-
# code copied from the WuenschParser project, needs to be merged into the
# "binary_parser.py" version.

from __future__ import absolute_import, print_function, unicode_literals

from collections import OrderedDict
import struct


__all__ = ['BinaryFormat']

class BinaryFormat(object):
    def __init__(self, bin_structure):
        self.field_formats = OrderedDict(bin_structure)
        self.format_string, self.field_names = combine_field_formats(bin_structure)

    @classmethod
    def from_dict(cls, fields_with_bin_structure):
        bin_structure = tuple(fields_with_bin_structure.items())
        return BinaryFormat(bin_structure)

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
        # LATER: we could verify that the length matches but that seems waste
        # right now as the generating program is quite ... "stable" (as in
        # "won't be updated in a major way").
        #values = raw_values
        #for length_and_value in pairwise(raw_values):
        #    raw_value = length_and_value[1]
        #    values.append(raw_value)
        values = raw_values
        if len(values) != len(self.field_names):
            msg_text = 'record contains %d fields but %d values parsed'
            raise ValueError(msg_text % (len(self.field_names), len(values)))
        name_value_pairs = zip(self.field_names, values)
        return OrderedDict(name_value_pairs)

    def to_bytes(self, kwargs, value_serializer=None):
        values = []
        for field_name in self.field_names:
            user_values = kwargs[field_name]
            if value_serializer is not None:
                field_format = self.field_formats[field_name]
                form_values = value_serializer(field_name, user_values, field_format)
            else:
                form_values = user_values

            if isinstance(form_values, (tuple, list)):
                values.extend(form_values)
            else:
                values.append(form_values)
        assert len(kwargs) == len(self.field_names)
        return struct.pack(self.format_string, *values)


def pairwise(iterable):
    a = iter(iterable)
    return zip(a, a)

def combine_field_formats(name_format_tuples):
    format_string = '<'  # little-endian byte ordering
    field_names = []
    for field_name, field_format in name_format_tuples:
        format_string += field_format
        field_names.append(field_name)
    return format_string, tuple(field_names)

