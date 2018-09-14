# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from struct import pack, calcsize

import six

from ..meta import BinaryMeta

if six.PY3:
    src = '''
class BinaryData(metaclass=BinaryMeta):
    _encoding = 'cp850'
    _struc = (
        ('str8',  '8s'),
        ('_ign4', '4s'),
        ('int1',  'i'),
    )
'''
else:
    src = '''
class BinaryData(object):
    __metaclass__ = BinaryMeta
    _encoding = 'cp850'
    _struc = (
        ('str8',  '8s'),
        ('_ign4', '4s'),
        ('int1',  'i'),
    )
'''
six.exec_(src, globals())


class TestBinaryMeta():

    def test_create(self):
        data = BinaryData(self._get_binary_data())

        assert data.record_size == 16
        assert data.format_string == '<8s4si'
        assert data.field_names == ('str8', '_ign4', 'int1')

        assert data._get_binary() == self._get_binary_data()

        assert data.rec.str8 == '12345678'
        assert data.rec.int1 == 87654321

        assert str(data) == """BinaryData:
    str8 = 12345678
    int1 = 87654321"""

    def test_field_class_is_class_attribute(self):
        data_1 = BinaryData(self._get_binary_data())
        data_2 = BinaryData(self._get_binary_data())

        assert data_1.Fields is data_2.Fields

    def test_len(self):
        data = BinaryData(self._get_binary_data())
        assert len(data) == 16

    def _get_binary_data(self):
        return pack('8s4si', b'12345678', b'XXXX', 87654321)

    def test_offset(self):
        data = BinaryData(self._get_binary_data())
        assert len(data) - data.field_offsets[2] == calcsize('i')
