# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import struct

from six import text_type, with_metaclass

from ddc.tool.tupletool import namedtuple


class BinaryMeta(type):

    def __new__(_mcs, _name, _bases, _dict):

        _remove, _helper, _type = None, None, type
        _remove = set(locals())

        if '_struc' not in _dict:
            return _type.__new__(_mcs, _name, _bases, _dict)

        _struc = _dict['_struc']
        _helper = _type.__new__(_mcs, _name, _bases, _dict)
        _debug = getattr(_helper, '_debug', False)

        def __init__(self, data, offset=0):
            if data is None:
                # explicitly pass None to inquire record_size without data
                return
            self.rec = self.get_fields(data, offset)
            self.offset = offset
            self.edited_fields = set()

        def _unpacker(self, data):
            if isinstance(data, int):
                return data
            asc = data.decode(self._encoding).split('\x00', 1)[0]
            return asc

        def get_fields(self, data, offset):
            ''' unpack the fields out of binary data and build a namedtuple '''
            try:
                unpacked = struct.unpack_from(self.format_string, data, offset)
            except struct.error as e:
                raise ValueError('probably corrupt data/offsets:\n'
                                 '    "{}"'.format(e))
            return Fields._make(list(map(self._unpacker, unpacked)))

        if _debug:
            # in order to get timing, we need to circumvent the buffer protocol
            def get_fields(self, data, offset):
                data = data[offset : offset + self.record_size]
                unpacked = struct.unpack(self.format_string, data)
                return Fields._make(list(map(self._unpacker, unpacked)))

        def _get_binary(self):
            conv = []
            for arg in self.rec:
                if isinstance(arg, text_type):
                    arg = arg.encode(self._encoding)
                conv.append(arg)
            ret = struct.pack(self.format_string, *conv)
            return ret

        def update_rec(self, **kw):
            ''' create an updated namedtuple '''
            self.rec = self.rec._replace(**kw)
            self.edited_fields |= set(kw)

        def is_dirty(self):
            return len(self.edited_fields) > 0

        def __eq__(self, other):
            return self.rec == other.rec

        def __ne__(self, other):
            return not(self == other)

        def __len__(self):
            return self.record_size

        def __str__(self):
            result = ['%s:' % self.__class__.__name__]
            for field_name in self.field_names:
                if (not field_name.startswith('_ign')) and (field_name != '_valid'):
                    str_part = '    %s = %s' % (field_name, getattr(self.rec, field_name))
                    result.append(str_part)
            return '\n'.join(result)

        format_string = '<'  # specific for Intel, needed to disable alignment
        field_names = []
        field_offsets = []
        for name, struc in _struc:
            field_offsets.append(struct.calcsize(format_string))
            field_names.append(name)
            format_string += struc
        del name, struc
        field_names = tuple(field_names)
        field_offsets = tuple(field_offsets)
        record_size = struct.calcsize(format_string)

        Fields = namedtuple('Fields', field_names, rename=True)

        _helper = dict((key, value) for (key, value) in list(locals().items())
                       if key not in _remove )
        _helper.update(_dict)

        ret = _type.__new__(_mcs, _name, _bases, _helper)
        assert hasattr(ret, '_encoding'), (
            'a database structure needs to define "_encoding"')
        return ret


from ddc.storage.cdb.cdb_format import CDB_ENCODING

class WithBinaryMeta(with_metaclass(BinaryMeta)):
    ''' helper class for python 2/3 compatibility '''

    _encoding = CDB_ENCODING
