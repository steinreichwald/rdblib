# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import struct

from ddc.compat import string_types


__all__ = ['BinaryFixture', 'UnclosableBytesIO']

class BinaryFixture(object):
    def __init__(self, values, bin_structure, encoding=None):
        self.values = values
        self.bin_structure = bin_structure
        # prevent recursive imports (and fixtues inherit from "BinaryFixture"
        # so they can't delay the import)
        from ddc.storage.cdb import CDB_ENCODING
        self.encoding = encoding or CDB_ENCODING
        self._assert_caller_used_only_known_fields(values, bin_structure)

    def _assert_caller_used_only_known_fields(self, values, bin_structure):
        known_field_names = set(dict(bin_structure))
        unknown_values = set(values).difference(known_field_names)
        if unknown_values:
            unknown_field = unknown_values.pop()
            raise TypeError('unknown field %r' % unknown_field)

    def as_bytes(self, values):
        buffer_ = BytesIO()
        for i, (key, format_) in enumerate(self.bin_structure):
            if key in values:
                value = values[key]
            elif key == 'number':
                value = i+1
            elif format_.endswith('s'):
                value = ''
            elif format_.endswith('i'):
                value = 0
            else:
                raise AssertionError('unexpected binary format')
            if isinstance(value, string_types):
                value = value.encode(self.encoding)
            bin_ = struct.pack(format_, value)
            buffer_.write(bin_)
        buffer_.seek(0)
        return buffer_.read()


class UnclosableBytesIO(BytesIO):
    """
    Behaves like a regular BytesIO instance but does not anything on .close()
    unless force=True is specified.
    This is useful for testing when we need to open/close binary files multiple
    times which is no problem with regular files but with BytesIO-backed data.
    """
    def close(self, force=False):
        if not force:
            return
        super(UnclosableBytesIO, self).close()

